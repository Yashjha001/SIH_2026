"""Official observation adapter. Activated only with an approved station mapping/access."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .providers import WeatherBundle, WeatherProvider


def parse_current(payload, station_id: str, now: datetime | None = None) -> dict:
    """Validate the documented IMD current_wx fields; reject wrong/stale stations."""
    rows = payload if isinstance(payload, list) else payload.get("data", [payload])
    if isinstance(rows, dict):
        rows = list(rows.values())
    row = next((item for item in rows if isinstance(item, dict) and str(item.get("Station Id")) == station_id), None)
    if row is None:
        raise ValueError("Mapped station missing from IMD response")
    stamp = datetime.fromisoformat(f"{row['Date of Observation']}T{row['Time of Observation']}").replace(tzinfo=timezone.utc)
    age = ((now or datetime.now(timezone.utc)) - stamp).total_seconds()
    if not -900 <= age <= 10800:
        raise ValueError("IMD observation is stale or future-dated")
    temperature, humidity, wind = float(row["Temperature"]), float(row["Humidity"]), float(row["Wind Speed"])
    if not (-70 <= temperature <= 65 and 0 <= humidity <= 100 and 0 <= wind <= 500):
        raise ValueError("Invalid IMD observation")
    return {"temperature": round(temperature), "humidity": round(humidity), "wind_speed": round(wind),
            "updated_at": f"IMD observation {stamp.isoformat()}", "source": "IMD observations + Open-Meteo forecast / CAMS AQI",
            "imd_status": "connected"}


class IMDEnrichedProvider(WeatherProvider):
    """Supplemental forecast remains available when official access is not approved."""
    URL = "https://api.imd.gov.in/api/v1/current_wx"

    def __init__(self, supplemental: WeatherProvider):
        self.supplemental = supplemental
        self.stations = json.loads(os.getenv("IMD_STATION_MAP", "{}"))
        self.authorization = os.getenv("IMD_AUTHORIZATION", "")

    def search(self, query: str):
        return self.supplemental.search(query)

    def bundle(self, location: str) -> WeatherBundle:
        bundle = self.supplemental.bundle(location)
        station = self.stations.get(location.casefold())
        if not station:
            return bundle
        try:
            headers = {"User-Agent": "MausamPlus/0.3"}
            if self.authorization:
                headers["Authorization"] = self.authorization
            request = Request(f"{self.URL}?{urlencode({'id': station})}", headers=headers)
            with urlopen(request, timeout=8) as response:
                updates = parse_current(json.loads(response.read()), str(station))
            sources = {"temperature": "IMD", "humidity": "IMD", "wind_speed": "IMD",
                       "feels_like": "Open-Meteo", "hourly": "Open-Meteo", "daily": "Open-Meteo",
                       "aqi": "CAMS via Open-Meteo"}
            weather = bundle.weather.model_copy(update={**updates, "field_sources": sources})
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            weather = bundle.weather.model_copy(update={"imd_status": "unavailable"})
        return WeatherBundle(weather, bundle.hourly, bundle.daily)
