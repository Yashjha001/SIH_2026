from datetime import datetime, timedelta, timezone
from urllib.error import URLError
import pytest

from app.imd import parse_current
from app.providers import OpenMeteoWeatherProvider


def payload():
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    times = [(start + timedelta(hours=i)).isoformat(timespec="minutes") for i in range(48)]
    current = {"time":datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="minutes"),
        "temperature_2m":25, "apparent_temperature":25, "relative_humidity_2m":60,
        "wind_speed_10m":5, "weather_code":0, "precipitation":0}
    hourly = {"time":times, "temperature_2m":[25]*48, "apparent_temperature":[25]*48,
        "relative_humidity_2m":[60]*48, "precipitation_probability":[90]*48,
        "weather_code":[0]*48, "visibility":[0]*48, "wind_speed_10m":[5]*48, "uv_index":[0]*48, "is_day":[1]*48}
    daily = {"time":[start.date().isoformat()], "weather_code":[0], "temperature_2m_max":[25],
        "temperature_2m_min":[20], "precipitation_probability_max":[90]}
    return {"current":current, "hourly":hourly, "daily":daily, "utc_offset_seconds":0}


def test_provider_preserves_zeroes_and_does_not_invent_hazards(monkeypatch):
    provider = OpenMeteoWeatherProvider()
    def get(url, params):
        if "geocoding" in url:
            return {"results":[{"name":"Test City","latitude":23,"longitude":72}]}
        if "air-quality" in url:
            raise URLError("AQI unavailable")
        return payload()
    monkeypatch.setattr(provider, "_get_json", get)
    bundle = provider.bundle("Test City")
    assert bundle.weather.uv_index == 0
    assert bundle.weather.visibility == 0
    assert bundle.weather.aqi is None
    assert bundle.weather.flood_risk == "unavailable"
    assert bundle.weather.lightning_probability == 0
    assert bundle.weather.cyclone_risk == "unavailable"
    assert len(bundle.hourly) == 24
    assert all(row["hours_ahead"] > 0 for row in bundle.hourly)


def test_weather_failure_does_not_return_mock(monkeypatch):
    provider = OpenMeteoWeatherProvider()
    def fail(*args):
        raise URLError("offline")
    monkeypatch.setattr(provider, "_get_json", fail)
    with pytest.raises(RuntimeError):
        provider.bundle("Ahmedabad")


def test_imd_station_freshness_and_units():
    now = datetime(2026,9,11,10,tzinfo=timezone.utc)
    row = {"Station Id":"42182", "Date of Observation":"2026-09-11", "Time of Observation":"09:00:00",
           "Temperature":"32.4", "Humidity":"72", "Wind Speed":"18"}
    parsed = parse_current([row], "42182", now)
    assert parsed["temperature"] == 32 and parsed["wind_speed"] == 18
    assert parsed["imd_status"] == "connected"
    with pytest.raises(ValueError):
        parse_current([row], "wrong", now)
    with pytest.raises(ValueError):
        parse_current([row], "42182", now + timedelta(days=2))
