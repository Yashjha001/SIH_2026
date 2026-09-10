from __future__ import annotations

from .schemas import Alert, Feed, Impact, Persona, Recommendation, UserProfile, Weather


def priority(score: int) -> str:
    if score >= 81: return "Critical"
    if score >= 61: return "High"
    if score >= 31: return "Moderate"
    return "Low"


def recommendation(persona: Persona, weather: Weather) -> Recommendation:
    common_heat = [f"Feels like {weather.feels_like}°C", f"UV index is {weather.uv_index} (high)"]
    options: dict[Persona, Recommendation] = {
        Persona.FITNESS: Recommendation(id="fitness-window", type="activity", title="Good morning for cycling", message="Best window: 6:00–8:00 AM", priority="High", score=78, reason=["Lower temperatures early morning", "UV rises sharply after 10 AM", "Rain chance is lower before noon"], action="Plan your ride before 8 AM", badge="Best time"),
        Persona.FAMILY: Recommendation(id="family-heat", type="family", title="Afternoon heat alert", message="Outdoor play may be uncomfortable after 12 PM.", priority="High", score=75, reason=common_heat + ["Rain is likely later in the day"], action="Choose indoor activities this afternoon", badge="Plan ahead"),
        Persona.AGRICULTURE: Recommendation(id="farm-rain", type="farm", title="Plan around tomorrow's rain", message="Review irrigation plans before the expected rainfall.", priority="Moderate", score=64, reason=["Rain probability is 60%", "Strong wind may affect spraying", "Temperature remains elevated"], action="Check your field plan before watering", badge="Demo recommendation"),
        Persona.TRAVEL: Recommendation(id="travel-pack", type="travel", title="Pack for a changeable evening", message="Carry rain protection and keep outdoor plans earlier.", priority="High", score=72, reason=["Rain probability is 60%", "Wind is 28 km/h", "Peak heat is expected in the afternoon"], action="Pack a light rain layer", badge="Destination advice"),
    }
    return options.get(persona, options[Persona.FITNESS])


def build_feed(profile: UserProfile, weather: Weather) -> Feed:
    main = recommendation(profile.persona, weather)
    factor_names = [
        {"name": "Temperature", "status": "High" if weather.feels_like >= 35 else "Moderate"},
        {"name": "UV", "status": "High" if weather.uv_index >= 7 else "Moderate"},
        {"name": "Rain", "status": "Moderate" if weather.rain_probability >= 40 else "Low"},
        {"name": "Wind", "status": "High" if weather.wind_speed >= 25 else "Moderate"},
    ]
    score = main.score
    alert = Alert(title="Heat and wind advisory", message="Strong wind and afternoon heat may affect outdoor plans.", severity="High")
    explanation = {
        "title": "Why am I seeing this?",
        "items": [f"You selected {profile.persona.value.title()}", *main.reason],
        "summary": "The weather is the same; the recommendation is ranked for what matters to you."
    }
    hourly = [
        {"time": "6 AM", "icon": "☀️", "temp": 25, "event": "Low UV"}, {"time": "9 AM", "icon": "🌤️", "temp": 29, "event": "Comfortable"},
        {"time": "12 PM", "icon": "☀️", "temp": 33, "event": "Peak heat"}, {"time": "3 PM", "icon": "💨", "temp": 34, "event": "Strong wind"},
        {"time": "6 PM", "icon": "🌧️", "temp": 30, "event": "Rain window"},
    ]
    daily = [
        {"day": "Today", "icon": "🌤️", "high": 34, "low": 25, "rain": 60}, {"day": "Thu", "icon": "🌧️", "high": 31, "low": 24, "rain": 75},
        {"day": "Fri", "icon": "🌤️", "high": 32, "low": 25, "rain": 35}, {"day": "Sat", "icon": "☀️", "high": 34, "low": 26, "rain": 15},
    ]
    return Feed(location={"name": profile.location, "label": "Active location"}, weather=weather,
        impact=Impact(score=score, level=priority(score), factors=factor_names), cards=[main], recommendations=[main], alerts=[alert],
        explanation=explanation, hourly=hourly, daily=daily)
