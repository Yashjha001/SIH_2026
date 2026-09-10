from datetime import datetime, timedelta

from app.engine import build_feed
from app.schemas import Persona, UserProfile, Weather


def calm(**changes):
    values = dict(location="Ahmedabad", temperature=24, feels_like=24, humidity=45, wind_speed=5,
        rain_probability=5, uv_index=1, aqi=30, visibility=20, condition="Clear sky",
        updated_at="test", source="Open-Meteo live forecast", lightning_probability=0, fog_probability=0)
    return Weather(**{**values, **changes})


def hour(time="2026-09-11T09:00", **changes):
    values = dict(timestamp=time, time=time, hours_ahead=1, temp=24, feels_like=24, humidity=45,
        rain=5, uv=1, wind=5, visibility=20, weather_code=0, is_day=1, event="Clear", icon="sun")
    return {**values, **changes}


def test_calm_weather_does_not_invent_warnings():
    feed = build_feed(UserProfile(activities=[]), calm())
    assert feed.alerts == [] and feed.notifications == []
    assert feed.impact.score == 0
    assert "6:00" not in str(feed.recommendations)
    assert feed.observations == []


def test_weather_changes_top_recommendation_and_all_scores_are_bounded():
    profile = UserProfile(persona=Persona.FAMILY)
    heat = build_feed(profile, calm(feels_like=44, temperature=40))
    rain = build_feed(profile, calm(rain_probability=95))
    assert heat.recommendations[0].id == "temperature"
    assert rain.recommendations[0].id == "rain"
    for feed in [heat, rain]:
        assert 0 <= feed.impact.score <= 100
        assert sum(f["contribution"] for f in feed.impact.factors) == feed.impact.score
        assert all(0 <= item.score <= 100 for item in feed.recommendations)
        assert all(alert.reason and alert.actions for alert in feed.alerts)


def test_personas_and_meaningful_preferences_change_relevance():
    weather = calm(wind_speed=45)
    general = build_feed(UserProfile(persona=Persona.GENERAL, activities=[]), weather)
    cyclist = build_feed(UserProfile(persona=Persona.FITNESS, activities=["Cycling"]), weather)
    custom = build_feed(UserProfile(persona=Persona.GENERAL, activities=["Music", "Books"]), weather)
    assert cyclist.recommendations[0].score > general.recommendations[0].score
    assert custom.impact.score == general.impact.score
    assert "Cycling" in " ".join(cyclist.recommendations[0].reason)


def test_humidity_visibility_and_protection_are_scored():
    weather = calm(feels_like=33, humidity=95, visibility=.2)
    standard = build_feed(UserProfile(persona=Persona.FAMILY, activities=[]), weather)
    protected = build_feed(UserProfile(persona=Persona.FAMILY, activities=[], extra_protection=["Children"]), weather)
    factors = {f["name"]: f["contribution"] for f in protected.impact.factors}
    assert factors["Humidity"] > 0 and factors["Visibility"] > 0
    assert protected.impact.score >= standard.impact.score
    assert {"Temperature","Rain","UV","Air quality","Wind","Lightning","Flooding","Cyclone"} <= factors.keys()


def test_departure_overlap_changes_ranking_and_explanation():
    weather = calm()
    rows = [hour(rain=65)]
    early = build_feed(UserProfile(persona=Persona.COMMUTER, activities=[], commute_time="09:00"), weather, rows)
    late = build_feed(UserProfile(persona=Persona.COMMUTER, activities=[], commute_time="18:00"), weather, rows)
    assert early.recommendations[0].score > late.recommendations[0].score
    assert "overlaps" in " ".join(early.recommendations[0].reason)


def test_window_is_future_daylight_and_uses_forecast_values():
    rows = [hour("2026-09-11T03:00", hours_ahead=1, is_day=0),
            hour("2026-09-11T10:00", hours_ahead=8, feels_like=44, uv=11),
            hour("2026-09-11T08:00", hours_ahead=6),
            hour("2026-09-10T08:00", hours_ahead=-18)]
    feed = build_feed(UserProfile(), calm(), rows)
    window = next(item for item in feed.recommendations if item.id == "activity-window")
    assert "2026-09-11T08:00" in window.action
    assert "2026-09-10" not in window.action


def test_notifications_respect_preferences_and_are_stable():
    weather = calm(feels_like=44, temperature=40)
    enabled = build_feed(UserProfile(), weather)
    repeat = build_feed(UserProfile(), weather)
    paused = build_feed(UserProfile(notifications_enabled=False), weather)
    assert enabled.notifications
    assert enabled.notifications[0].id == repeat.notifications[0].id
    assert paused.notifications == [] and paused.alerts


def test_rain_alone_does_not_generate_cyclone_flood_or_lightning_claims():
    feed = build_feed(UserProfile(persona=Persona.TRAVEL), calm(rain_probability=100))
    text = " ".join(alert.title for alert in feed.alerts)
    assert "Lightning" not in text and "Flooding" not in text and "Cyclone" not in text
    assert all(alert.distance_km is None and alert.eta_minutes is None for alert in feed.alerts)


def test_critical_weather_precedes_moderate_and_demo_does_not_notify():
    feed = build_feed(UserProfile(), calm(thunderstorm=True, uv_index=7))
    assert feed.alerts[0].severity == "Critical"
    demo = build_feed(UserProfile(), calm(thunderstorm=True, source="Mausam+ demo scenario"))
    assert demo.is_demo_data and not demo.notifications
