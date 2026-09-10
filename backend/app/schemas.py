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


class Impact(BaseModel):
    score: int
    level: str
    label: str = "Personalized Weather Impact"
    factors: list[dict[str, str]]


class UserProfile(BaseModel):
    id: str = "demo-user"
    name: str = "Aarav"
    persona: Persona = Persona.FITNESS
    location: str = "Ahmedabad"
    activities: list[str] = ["Cycling"]
    notifications_enabled: bool = True


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
    is_demo_data: bool = True


class LocationInput(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    label: str = Field(default="Other", max_length=32)
