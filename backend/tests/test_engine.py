from app.engine import build_feed
from app.providers import MockWeatherProvider
from app.schemas import Persona, UserProfile

def test_same_weather_creates_persona_specific_recommendations():
    weather = MockWeatherProvider().current("Ahmedabad")
    fitness = build_feed(UserProfile(persona=Persona.FITNESS), weather)
    family = build_feed(UserProfile(persona=Persona.FAMILY), weather)
    farm = build_feed(UserProfile(persona=Persona.AGRICULTURE), weather)
    travel = build_feed(UserProfile(persona=Persona.TRAVEL), weather)
    assert fitness.weather == family.weather == farm.weather == travel.weather
    assert "cycling" in fitness.recommendations[0].title.lower()
    assert "heat" in family.recommendations[0].title.lower()
    assert "rain" in farm.recommendations[0].title.lower()
    assert "pack" in travel.recommendations[0].title.lower()
