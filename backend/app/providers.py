from __future__ import annotations

from abc import ABC, abstractmethod
from .schemas import Weather


class WeatherProvider(ABC):
    @abstractmethod
    def current(self, location: str) -> Weather: ...


class MockWeatherProvider(WeatherProvider):
    """Transparent, fixed scenario data for the MVP demonstration."""
    def current(self, location: str) -> Weather:
        conditions = {
            "Ahmedabad": (34, 38, 52, 28, 60, 9, 142, 5.2, "Hazy sunshine", 34, "moderate", 10, "low", "none"),
            "Mumbai": (29, 33, 79, 22, 80, 6, 78, 4.1, "Light rain", 48, "high", 8, "low", "watch"),
            "Delhi": (39, 43, 38, 20, 10, 9, 226, 3.4, "Hot and hazy", 8, "low", 28, "moderate", "none"),
        }
        temperature, feels_like, humidity, wind, rain, uv, aqi, visibility, condition, lightning, flood, fog, dust, cyclone = conditions.get(location, conditions["Ahmedabad"])
        return Weather(location=location, temperature=temperature, feels_like=feels_like,
            humidity=humidity, wind_speed=wind, rain_probability=rain, uv_index=uv,
            aqi=aqi, visibility=visibility, condition=condition, updated_at="Updated just now",
            lightning_probability=lightning, flood_risk=flood, fog_probability=fog,
            dust_risk=dust, cyclone_risk=cyclone)
