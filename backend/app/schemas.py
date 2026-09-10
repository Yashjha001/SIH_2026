from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Persona(str, Enum):
    FITNESS = "fitness"
    FAMILY = "family"
    AGRICULTURE = "agriculture"
    TRAVEL = "travel"
    HEALTH = "health"
    COMMUTER = "commuter"
    BEACH = "beach"
    EVENT = "event"
    OUTDOOR_WORKER = "outdoor_worker"
    GENERAL = "general"


class Weather(BaseModel):
    location: str
    temperature: int
    feels_like: int
    humidity: int = Field(ge=0, le=100)
    wind_speed: int = Field(ge=0)
    rain_probability: int = Field(ge=0, le=100)
    uv_index: int = Field(ge=0, le=15)
    aqi: int | None = None
    visibility: float
    condition: str
    updated_at: str
    lightning_probability: int = Field(default=18, ge=0, le=100)
    flood_risk: str = "low"
    fog_probability: int = Field(default=8, ge=0, le=100)
    dust_risk: str = "low"
    cyclone_risk: str = "none"


class Recommendation(BaseModel):
    id: str
    type: str
    title: str
    message: str
    priority: str
    score: int
    reason: list[str]
    action: str
    badge: str | None = None


class Alert(BaseModel):
    title: str
    message: str
    severity: str
    source: str = "Demo rule"
    source_type: str = "generated"
    distance_km: float | None = None
    eta_minutes: int | None = None
    actions: list[str] = Field(default_factory=list)


class Impact(BaseModel):
    score: int
    level: str
    label: str = "Personalized Weather Impact"
    factors: list[dict[str, str | int]]


class UserProfile(BaseModel):
    id: str = "demo-user"
    name: str = "Aarav"
    persona: Persona = Persona.FITNESS
    location: str = "Ahmedabad"
    activities: list[str] = ["Cycling"]
    notifications_enabled: bool = True
    extra_protection: list[str] = Field(default_factory=list)
    commute_time: str | None = None
    routine: str | None = None


class CommunityObservation(BaseModel):
    id: str
    type: str
    location: str
    distance_km: float
    reported_at: str
    count: int = 1
    source_type: str = "community"
    verified: bool = False


class ObservationInput(BaseModel):
    type: str = Field(pattern="^(rainfall|waterlogging|fallen_tree|flooded_road|hail|lightning|strong_wind|fog)$")
    location: str = Field(min_length=2, max_length=80)


class Feed(BaseModel):
    location: dict[str, str]
    weather: Weather
    impact: Impact
    cards: list[Recommendation]
    recommendations: list[Recommendation]
    alerts: list[Alert]
    explanation: dict[str, list[str] | str]
    hourly: list[dict[str, str | int]]
    daily: list[dict[str, str | int]]
    observations: list[CommunityObservation] = Field(default_factory=list)
    is_demo_data: bool = True


class LocationInput(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    label: str = Field(default="Other", max_length=32)
