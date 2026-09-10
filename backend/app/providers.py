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
            "Ahmedabad": (34, 38, 52, 28, 60, 9, "Hazy sunshine"),
            "Mumbai": (29, 33, 79, 22, 80, 6, "Light rain"),
            "Delhi": (35, 40, 44, 20, 20, 8, "Sunny"),
        }
        temperature, feels_like, humidity, wind, rain, uv, condition = conditions.get(location, conditions["Ahmedabad"])
        return Weather(location=location, temperature=temperature, feels_like=feels_like,
            humidity=humidity, wind_speed=wind, rain_probability=rain, uv_index=uv,
            aqi=142, visibility=5.2, condition=condition, updated_at="Updated just now")
