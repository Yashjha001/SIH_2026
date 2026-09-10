from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from .schemas import LocationSearchResult, Weather


@dataclass
class WeatherBundle:
    weather: Weather
    hourly: list[dict[str, str | int]]
    daily: list[dict[str, str | int]]


class WeatherProvider(ABC):
    @abstractmethod
    def bundle(self, location: str) -> WeatherBundle: ...

    def current(self, location: str) -> Weather:
        return self.bundle(location).weather

    def search(self, query: str) -> list[LocationSearchResult]:
        return []


def _condition(code: int) -> tuple[str, str]:
    if code == 0: return "Clear sky", "☀️"
    if code in {1, 2}: return "Partly cloudy", "🌤️"
    if code == 3: return "Overcast", "☁️"
    if code in {45, 48}: return "Fog", "🌫️"
    if code in {51, 53, 55, 56, 57}: return "Drizzle", "🌦️"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}: return "Rain", "🌧️"
    if code in {71, 73, 75, 77, 85, 86}: return "Snow", "🌨️"
    if code in {95, 96, 99}: return "Thunderstorm", "⛈️"
    return "Variable weather", "🌤️"


class MockWeatherProvider(WeatherProvider):
    """Safe fallback used only when the live provider cannot be reached."""

    def bundle(self, location: str) -> WeatherBundle:
        conditions = {
            "Ahmedabad": (34, 38, 52, 28, 60, 9, 142, 5.2, "Hazy sunshine", 34, "moderate", 10, "low", "none"),
            "Mumbai": (29, 33, 79, 22, 80, 6, 78, 4.1, "Light rain", 48, "high", 8, "low", "watch"),
            "Delhi": (39, 43, 38, 20, 10, 9, 226, 3.4, "Hot and hazy", 8, "low", 28, "moderate", "none"),
        }
        values = conditions.get(location, conditions["Ahmedabad"])
        temperature, feels_like, humidity, wind, rain, uv, aqi, visibility, condition, lightning, flood, fog, dust, cyclone = values
        weather = Weather(location=location, temperature=temperature, feels_like=feels_like,
            humidity=humidity, wind_speed=wind, rain_probability=rain, uv_index=uv,
            aqi=aqi, visibility=visibility, condition=condition, updated_at="Fallback data",
            lightning_probability=lightning, flood_risk=flood, fog_probability=fog,
            dust_risk=dust, cyclone_risk=cyclone, source="Mausam+ demo scenario", severe_data_available=True,
            thunderstorm=lightning >= 30)
        hourly = [
            {"time":"6 AM","icon":"☀️","temp":temperature-7,"event":"Lower exposure"},
            {"time":"9 AM","icon":"🌤️","temp":temperature-4,"event":"UV rising"},
            {"time":"12 PM","icon":"☀️","temp":temperature-1,"event":"Peak heat"},
            {"time":"3 PM","icon":"💨","temp":temperature,"event":"Stronger wind"},
            {"time":"6 PM","icon":"🌧️","temp":temperature-4,"event":"Rain window"},
        ]
        daily = [{"day":day,"icon":"🌤️" if i != 1 else "🌧️","high":temperature-i%2,"low":temperature-9,"rain":min(95,max(5,rain+i*3))}
                 for i, day in enumerate(["Today","Tomorrow","Day 3","Day 4","Day 5","Day 6","Day 7"])]
        return WeatherBundle(weather, hourly, daily)


class OpenMeteoWeatherProvider(WeatherProvider):
    """Live global forecast adapter with a short cache. Demo data is opt-in."""

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(self, fallback: WeatherProvider | None = None, ttl_seconds: int = 300):
        self.fallback = fallback or MockWeatherProvider()
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, WeatherBundle]] = {}
        self._lock = Lock()

    def search(self, query: str) -> list[LocationSearchResult]:
        if len(query.strip()) < 2: return []
        payload = self._get_json(self.GEOCODING_URL, {"name": query.strip(), "count": 8, "language": "en", "format": "json"})
        return [LocationSearchResult(name=item["name"], admin1=item.get("admin1"), country=item.get("country"),
                    latitude=item["latitude"], longitude=item["longitude"])
                for item in payload.get("results", [])]

    @staticmethod
    def _get_json(url: str, params: dict[str, str | int | float]) -> dict:
        request = Request(f"{url}?{urlencode(params)}", headers={"User-Agent":"MausamPlus/0.2"})
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))

    def _coordinates(self, location: str) -> LocationSearchResult:
        results = self.search(location)
        if not results: raise ValueError(f"Location not found: {location}")
        return results[0]

    def bundle(self, location: str) -> WeatherBundle:
        key = location.strip().casefold()
        cached = self._cache.get(key)
        if cached and monotonic() - cached[0] < self.ttl_seconds: return cached[1]
        try:
            result = self._live_bundle(location)
            with self._lock: self._cache[key] = (monotonic(), result)
            return result
        except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("Live weather is temporarily unavailable; retry shortly.") from exc

    def _live_bundle(self, location: str) -> WeatherBundle:
        place = self._coordinates(location)
        params = {
            "latitude": place.latitude, "longitude": place.longitude, "timezone": "auto", "forecast_days": 7,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,precipitation",
            "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation_probability,weather_code,visibility,wind_speed_10m,uv_index,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        }
        payload = self._get_json(self.FORECAST_URL, params)
        try:
            air_payload = self._get_json(self.AIR_URL, {"latitude": place.latitude, "longitude": place.longitude,
                "timezone":"auto", "current":"us_aqi,dust"})
        except (HTTPError, URLError, TimeoutError, ValueError):
            air_payload = {}
        air = air_payload.get("current", {})
        current, hourly_data, daily_data = payload["current"], payload["hourly"], payload["daily"]
        condition, _ = _condition(int(current["weather_code"]))
        aqi = air.get("us_aqi")
        dust = float(air.get("dust") or 0)
        local_now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=payload.get("utc_offset_seconds", 0))
        current_hour = local_now.replace(minute=0, second=0, microsecond=0).isoformat(timespec="minutes")
        try: current_index = hourly_data["time"].index(current_hour)
        except ValueError: current_index = 0
        visibility = float(hourly_data["visibility"][current_index]) / 1000
        rain_probability = round(hourly_data["precipitation_probability"][current_index])
        uv_index = round(hourly_data["uv_index"][current_index])
        code = int(current["weather_code"])
        weather = Weather(
            location=place.name, temperature=round(current["temperature_2m"]), feels_like=round(current["apparent_temperature"]),
            humidity=round(current["relative_humidity_2m"]), wind_speed=round(current["wind_speed_10m"]),
            rain_probability=rain_probability, uv_index=max(0,min(15,uv_index)), aqi=round(aqi) if aqi is not None else None,
            visibility=round(visibility,1), condition=condition, updated_at=f"Live · {current['time'].replace('T',' ')}",
            lightning_probability=0, flood_risk="unavailable", cyclone_risk="unavailable",
            fog_probability=0, dust_risk="moderate" if dust >= 20 else "low",
            thunderstorm=code in {95,96,99}, rainfall_mm=current.get("precipitation"),
            source="Open-Meteo live forecast", latitude=place.latitude, longitude=place.longitude)
        indices = range(current_index + 1, min(current_index + 25, len(hourly_data["time"])))
        hourly = []
        for i in indices:
            timestamp = hourly_data["time"][i]
            label = datetime.fromisoformat(timestamp).strftime("%a %I %p")
            event, icon = _condition(int(hourly_data["weather_code"][i]))
            probability = int(hourly_data["precipitation_probability"][i] or 0)
            hourly.append({"time":label,"icon":icon,"temp":round(hourly_data["temperature_2m"][i]),"event":event,
                "timestamp":timestamp, "hours_ahead": i-current_index,
                "feels_like":round(hourly_data["apparent_temperature"][i]), "humidity":round(hourly_data["relative_humidity_2m"][i]),
                "rain":probability, "uv":min(15, round(hourly_data["uv_index"][i])), "wind":round(hourly_data["wind_speed_10m"][i]),
                "visibility":round(hourly_data["visibility"][i]/1000), "is_day":hourly_data["is_day"][i],
                "weather_code":hourly_data["weather_code"][i]})
        daily = []
        for i, iso_day in enumerate(daily_data["time"]):
            condition_day, icon = _condition(int(daily_data["weather_code"][i]))
            day = "Today" if i == 0 else "Tomorrow" if i == 1 else datetime.fromisoformat(iso_day).strftime("%a")
            daily.append({"day":day,"date":iso_day,"condition":condition_day,"icon":icon,"high":round(daily_data["temperature_2m_max"][i]),
                "low":round(daily_data["temperature_2m_min"][i]),"rain":round(daily_data["precipitation_probability_max"][i] or 0)})
        return WeatherBundle(weather, hourly, daily)
