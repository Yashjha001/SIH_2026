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


def test_context_changes_score_and_exposes_contributions():
    weather = MockWeatherProvider().current("Delhi")
    general = build_feed(UserProfile(persona=Persona.GENERAL), weather)
    worker = build_feed(UserProfile(persona=Persona.OUTDOOR_WORKER, extra_protection=["Outdoor workers"]), weather)
    assert worker.impact.score > general.impact.score
    assert sum(factor["contribution"] for factor in worker.impact.factors) >= worker.impact.score
    assert "break" in worker.recommendations[0].action.lower()


def test_commute_routine_changes_the_recommendation_reason():
    weather = MockWeatherProvider().current("Ahmedabad")
    commute = build_feed(UserProfile(persona=Persona.COMMUTER, commute_time="8:30 AM"), weather)
    assert "8:30 AM" in commute.recommendations[0].reason[-1]
    assert "commute" in commute.recommendations[0].title.lower()
