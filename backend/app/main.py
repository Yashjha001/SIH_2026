from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .engine import build_feed
from .providers import MockWeatherProvider, OpenMeteoWeatherProvider
from .schemas import CommunityObservation, LocationInput, ObservationInput, Persona, PreferencesUpdate, UserProfile
from .store import Store
from .imd import IMDEnrichedProvider

app = FastAPI(title="Mausam+ API", version="0.2.0", description="Live weather personalization API with transparent fallback")
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
provider = IMDEnrichedProvider(OpenMeteoWeatherProvider())
store = Store()
locations: dict[str, list[dict[str, str]]] = {"demo-user": [{"id": "home", "name": "Ahmedabad", "label": "Home"}, {"id": "travel", "name": "Mumbai", "label": "Destination"}]}

def profile_for(user_id: str) -> UserProfile:
    profile = store.profile(user_id)
    if profile is None: raise HTTPException(404, "User not found")
    return profile

@app.exception_handler(RuntimeError)
async def unavailable(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Live weather is temporarily unavailable. Please retry."})

@app.get("/api/health")
def health() -> dict[str, str]: return {"status": "healthy", "provider": "open-meteo", "model_version": "mausam-rules-2.0"}

@app.get("/api/model/status")
def model_status():
    return {
        "status": "rules_ready",
        "version": "mausam-rules-2.0",
        "imd": "Configured observation adapter; check feed status" if provider.stations else "Official IMD access is not configured; current source is Open-Meteo",
        "limitations": ["Heuristic planning scores are not calibrated risk probabilities", "Official severe-warning feed not connected"],
        "weather_prediction": "Open-Meteo numerical weather prediction models",
        "personalization": "deterministic explainable risk-scoring rules",
        "training": "not applicable to the current rule engine",
        "validation": "automated persona, hazard, scoring, preference, and API tests",
    }

@app.get("/api/locations/search")
def search_locations(q: str):
    if len(q.strip()) < 2: return []
    try: return provider.search(q)
    except Exception as exc: raise HTTPException(503, "Location search is temporarily unavailable") from exc

@app.get("/api/weather/current")
def current_weather(location: str = "Ahmedabad"):
    return provider.current(location)

@app.get("/api/weather/hourly")
def hourly_weather(location: str = "Ahmedabad"):
    return provider.bundle(location).hourly

@app.get("/api/weather/daily")
def daily_weather(location: str = "Ahmedabad"):
    return provider.bundle(location).daily

@app.get("/api/weather/alerts")
def weather_alerts(location: str = "Ahmedabad", persona: Persona = Persona.GENERAL):
    bundle = provider.bundle(location)
    return build_feed(UserProfile(location=location, persona=persona), bundle.weather, bundle.hourly, bundle.daily).alerts

@app.get("/api/users/{user_id}")
def get_user(user_id: str) -> UserProfile: return profile_for(user_id)

@app.put("/api/users/{user_id}")
def update_user(user_id: str, profile: UserProfile) -> UserProfile:
    if profile.id != user_id: raise HTTPException(400, "Profile id must match URL")
    profile_for(user_id)
    return store.save_profile(profile)

@app.get("/api/users/{user_id}/preferences")
def get_preferences(user_id: str):
    profile = profile_for(user_id)
    return {"activities": profile.activities, "extra_protection": profile.extra_protection,
            "notifications_enabled": profile.notifications_enabled, "commute_time": profile.commute_time,
            "routine": profile.routine}

@app.put("/api/users/{user_id}/preferences")
def update_preferences(user_id: str, changes: PreferencesUpdate):
    profile = profile_for(user_id)
    values = changes.model_dump(exclude_unset=True)
    if any(value is None for key, value in values.items() if key not in {"commute_time", "routine"}):
        raise HTTPException(422, "Preferences cannot be null")
    updated = UserProfile.model_validate({**profile.model_dump(), **values})
    return store.save_profile(updated)

@app.get("/api/users/{user_id}/personalized-feed")
def feed(user_id: str, persona: Persona | None = None, location: str | None = None):
    profile = profile_for(user_id).model_copy(update={"persona": persona or profile_for(user_id).persona, "location": location or profile_for(user_id).location})
    bundle = provider.bundle(profile.location)
    result = build_feed(profile, bundle.weather, bundle.hourly, bundle.daily)
    result.observations = store.reports(profile.location)
    read = store.read_ids(user_id)
    result.notifications = [alert for alert in result.notifications if alert.id not in read][:3]
    return result

@app.post("/api/users/{user_id}/notifications/{alert_id}/read", status_code=204)
def read_notification(user_id: str, alert_id: str):
    profile_for(user_id)
    store.mark_read(user_id, alert_id)

@app.get("/api/users/{user_id}/recommendations")
def recommendations(user_id: str): return feed(user_id).recommendations

@app.get("/api/users/{user_id}/alerts")
def alerts(user_id: str): return feed(user_id).alerts

@app.get("/api/users/{user_id}/locations")
def get_locations(user_id: str):
    profile_for(user_id); return locations.get(user_id, [])

@app.post("/api/users/{user_id}/locations", status_code=201)
def add_location(user_id: str, item: LocationInput):
    profile_for(user_id)
    entry = {"id": item.name.lower().replace(" ", "-"), "name": item.name, "label": item.label}
    if any(saved["id"] == entry["id"] for saved in locations.setdefault(user_id, [])):
        raise HTTPException(409, "Location already saved")
    locations.setdefault(user_id, []).append(entry)
    return entry

@app.delete("/api/locations/{location_id}", status_code=204)
def delete_location(location_id: str):
    for entries in locations.values():
        for entry in entries[:]:
            if entry["id"] == location_id: entries.remove(entry); return
    raise HTTPException(404, "Location not found")

@app.get("/api/demo/scenarios")
def scenarios(): return [{"id": p.value, "label": p.value.title()} for p in [Persona.FITNESS, Persona.FAMILY, Persona.AGRICULTURE, Persona.TRAVEL]]

@app.post("/api/demo/scenarios/{scenario_id}")
def select_scenario(scenario_id: Persona):
    bundle = MockWeatherProvider().bundle("Ahmedabad")
    return build_feed(UserProfile(persona=scenario_id), bundle.weather, bundle.hourly, bundle.daily)

@app.get("/api/community/observations")
def observations(location: str = "Ahmedabad"):
    return store.reports(location)

@app.post("/api/community/observations", status_code=201)
def report_observation(item: ObservationInput):
    if len(item.location.strip()) < 2:
        raise HTTPException(422, "A valid city is required")
    return store.report(item)
