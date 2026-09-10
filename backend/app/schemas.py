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
    source: str = "Mausam+ demo provider"
    imd_status: str = "not_configured"
    field_sources: dict[str, str] = Field(default_factory=dict)
    severe_data_available: bool = False
    rainfall_mm: float | None = None
    thunderstorm: bool = False
    latitude: float | None = None
    longitude: float | None = None


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
    id: str = ""
    title: str
    message: str
    severity: str
    source: str = "Demo rule"
    source_type: str = "generated"
    distance_km: float | None = None
    eta_minutes: int | None = None
    actions: list[str] = Field(default_factory=list)
    reason: list[str] = Field(default_factory=list)
    rank: int = 0
    location: str = ""
    valid_at: str = ""
    notification_eligible: bool = False


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
    commute_time: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    routine: str | None = Field(default=None, max_length=200)


class PreferencesUpdate(BaseModel):
    location: str | None = Field(default=None, min_length=2, max_length=80)
    persona: Persona | None = None
    activities: list[str] | None = None
    notifications_enabled: bool | None = None
    extra_protection: list[str] | None = None
    commute_time: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    routine: str | None = Field(default=None, max_length=200)


class CommunityObservation(BaseModel):
    id: str
    type: str
    location: str
    distance_km: float | None = None
    reported_at: str
    count: int = 1
    source_type: str = "community"
    verified: bool = False
    area: str = ""
    details: str = ""


class ObservationInput(BaseModel):
    type: str = Field(pattern="^(rainfall|waterlogging|fallen_tree|flooded_road|hail|lightning|strong_wind|fog)$")
    location: str = Field(min_length=2, max_length=80)
    area: str = Field(default="", max_length=120)
    details: str = Field(default="", max_length=500)


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
    provider: str = "Mausam+ demo provider"
    notifications: list[Alert] = Field(default_factory=list)
    notifications_enabled: bool = True
    model_version: str = "mausam-rules-2.0"
    data_gaps: list[str] = Field(default_factory=list)


class LocationSearchResult(BaseModel):
    name: str
    admin1: str | None = None
    country: str | None = None
    latitude: float
    longitude: float


class LocationInput(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    label: str = Field(default="Other", max_length=32)
