from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .engine import build_feed
from .providers import MockWeatherProvider
from .schemas import CommunityObservation, LocationInput, ObservationInput, Persona, UserProfile

app = FastAPI(title="Mausam+ API", version="0.1.0", description="Transparent demo weather personalization API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
provider = MockWeatherProvider()
profiles: dict[str, UserProfile] = {"demo-user": UserProfile()}
locations: dict[str, list[dict[str, str]]] = {"demo-user": [{"id": "home", "name": "Ahmedabad", "label": "Home"}, {"id": "travel", "name": "Mumbai", "label": "Destination"}]}
community_observations: list[CommunityObservation] = []

def profile_for(user_id: str) -> UserProfile:
    if user_id not in profiles: raise HTTPException(404, "User not found")
    return profiles[user_id]

@app.get("/api/health")
def health() -> dict[str, str]: return {"status": "healthy", "provider": "mock"}

@app.get("/api/weather/current")
def current_weather(location: str = "Ahmedabad"):
    return provider.current(location)

@app.get("/api/weather/hourly")
def hourly_weather(location: str = "Ahmedabad"):
    return build_feed(UserProfile(location=location), provider.current(location)).hourly

@app.get("/api/weather/daily")
def daily_weather(location: str = "Ahmedabad"):
    return build_feed(UserProfile(location=location), provider.current(location)).daily

@app.get("/api/weather/alerts")
def weather_alerts(location: str = "Ahmedabad", persona: Persona = Persona.GENERAL):
    return build_feed(UserProfile(location=location, persona=persona), provider.current(location)).alerts

@app.get("/api/users/{user_id}")
def get_user(user_id: str) -> UserProfile: return profile_for(user_id)

@app.put("/api/users/{user_id}")
def update_user(user_id: str, profile: UserProfile) -> UserProfile:
    if profile.id != user_id: raise HTTPException(400, "Profile id must match URL")
    profiles[user_id] = profile
    return profile

@app.get("/api/users/{user_id}/preferences")
def get_preferences(user_id: str):
    profile = profile_for(user_id)
    return {"activities": profile.activities, "extra_protection": profile.extra_protection,
            "notifications_enabled": profile.notifications_enabled, "commute_time": profile.commute_time,
            "routine": profile.routine}

@app.put("/api/users/{user_id}/preferences")
def update_preferences(user_id: str, profile: UserProfile):
    return update_user(user_id, profile)

@app.get("/api/users/{user_id}/personalized-feed")
def feed(user_id: str, persona: Persona | None = None, location: str | None = None):
    profile = profile_for(user_id).model_copy(update={"persona": persona or profile_for(user_id).persona, "location": location or profile_for(user_id).location})
    return build_feed(profile, provider.current(profile.location))

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
    profiles["demo-user"] = profiles["demo-user"].model_copy(update={"persona": scenario_id})
    return feed("demo-user")

@app.get("/api/community/observations")
def observations(location: str = "Ahmedabad"):
    defaults = build_feed(UserProfile(location=location), provider.current(location)).observations
    return [*community_observations, *defaults]

@app.post("/api/community/observations", status_code=201)
def report_observation(item: ObservationInput):
    observation = CommunityObservation(id=f"community-{len(community_observations)+1}", type=item.type,
        location=item.location, distance_km=0.5, reported_at="just now")
    community_observations.insert(0, observation)
    return observation
