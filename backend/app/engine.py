from __future__ import annotations

from .schemas import Alert, CommunityObservation, Feed, Impact, Persona, Recommendation, UserProfile, Weather


def priority(score: int) -> str:
    if score >= 81:
        return "Critical"
    if score >= 61:
        return "High"
    if score >= 31:
        return "Moderate"
    return "Low"


def _factor(name: str, contribution: int, explanation: str) -> dict[str, str | int]:
    status = "High" if contribution >= 18 else "Moderate" if contribution >= 8 else "Low"
    return {"name": name, "status": status, "contribution": contribution, "explanation": explanation}


def impact_for(profile: UserProfile, weather: Weather) -> Impact:
    persona = profile.persona
    outdoor = persona in {Persona.FITNESS, Persona.FAMILY, Persona.OUTDOOR_WORKER, Persona.EVENT}
    heat = 25 if weather.feels_like >= 42 and outdoor else 18 if weather.feels_like >= 36 and outdoor else 6
    uv = 18 if weather.uv_index >= 8 and outdoor else 8 if weather.uv_index >= 6 else 2
    rain_weight = 16 if persona in {Persona.COMMUTER, Persona.TRAVEL, Persona.FAMILY, Persona.AGRICULTURE} else 8
    rain = rain_weight if weather.rain_probability >= 60 else 4
    wind = 14 if weather.wind_speed >= 25 and persona in {Persona.FITNESS, Persona.OUTDOOR_WORKER, Persona.EVENT, Persona.AGRICULTURE} else 5
    air = 18 if (weather.aqi or 0) >= 200 else 10 if (weather.aqi or 0) >= 120 else 2
    context = {Persona.OUTDOOR_WORKER: 22, Persona.FITNESS: 18, Persona.FAMILY: 12, Persona.COMMUTER: 14, Persona.TRAVEL: 10, Persona.AGRICULTURE: 8}.get(persona, 6)
    if profile.extra_protection:
        context += min(8, len(profile.extra_protection) * 2)
    factors = [
        _factor("Temperature", heat, f"Feels like {weather.feels_like}°C during the warmest period"),
        _factor("UV", uv, f"UV index reaches {weather.uv_index}"),
        _factor("Rain", rain, f"Rain probability is {weather.rain_probability}%"),
        _factor("Wind", wind, f"Sustained wind is {weather.wind_speed} km/h"),
        _factor("Air quality", air, f"AQI is {weather.aqi or 'unavailable'}"),
        _factor("Your context", context, f"Ranked for {persona.value.replace('_', ' ')} and selected protection needs"),
    ]
    score = min(100, sum(int(f["contribution"]) for f in factors))
    return Impact(score=score, level=priority(score), factors=factors)


def _rec(id: str, type: str, title: str, message: str, score: int, reasons: list[str], action: str, badge: str) -> Recommendation:
    return Recommendation(id=id, type=type, title=title, message=message, priority=priority(score), score=score,
                          reason=reasons, action=action, badge=badge)


def recommendations_for(profile: UserProfile, weather: Weather, impact: Impact) -> list[Recommendation]:
    p, score = profile.persona, impact.score
    options: dict[Persona, list[Recommendation]] = {
        Persona.FITNESS: [
            _rec("fitness-window", "fitness", "Good morning for cycling", "Best window: 6:00–8:00 AM", score,
                 ["Lower temperature early morning", "UV rises after 10 AM", "Strong wind develops later"], "Plan your ride before 8 AM", "Best time"),
            _rec("fitness-heat", "fitness", "Avoid strenuous activity at midday", "Heat and UV peak between 11 AM–4 PM", score-5,
                 ["High feels-like temperature", "UV index is high"], "Choose shade or an indoor workout", "Preventive action"),
            _rec("fitness-rain", "fitness", "Rain may affect the evening session", "The likely rain window begins after 6 PM", score-12,
                 [f"Rain probability is {weather.rain_probability}%"], "Keep an indoor alternative ready", "Plan ahead"),
        ],
        Persona.FAMILY: [
            _rec("family-heat", "family", "Afternoon heat makes outdoor conditions uncomfortable", "Heat and UV rise after 11 AM", score,
                 ["Children are included in your protection preferences", "Feels-like temperature is elevated", "UV is high"], "Choose indoor activities after 11 AM", "Family alert"),
            _rec("family-commute", "family", "Rain may overlap with school travel", "Showers are most likely around the evening commute", score-5,
                 [f"Rain probability is {weather.rain_probability}%", "The rain window overlaps common pickup times"], "Carry rain protection for pickup", "School commute"),
            _rec("family-window", "family", "Earlier outdoor time is more comfortable", "The best family window is 7:00–9:00 AM", score-10,
                 ["Lower morning heat", "Lower morning UV"], "Move outdoor play to the morning", "Best time"),
        ],
        Persona.AGRICULTURE: [
            _rec("farm-rain", "agriculture", "Rain expected later today", "Review weather-dependent field activities", score,
                 [f"Rain probability is {weather.rain_probability}%", f"Wind reaches {weather.wind_speed} km/h"], "Review irrigation plans before rainfall", "Demo recommendation"),
            _rec("farm-wind", "agriculture", "Wind may affect exposed work", "Stronger afternoon winds reduce the suitable field window", score-5,
                 ["Wind exceeds the demo planning threshold"], "Check an official agrometeorological advisory before acting", "Demo rule"),
            _rec("farm-source", "agriculture", "Official advisory should guide crop decisions", "Mausam+ can surface approved Meghdoot or IMD guidance when connected", 25,
                 ["No verified agronomic advisory provider is connected in this prototype"], "Use this demo as weather context only", "Source transparency"),
        ],
        Persona.TRAVEL: [
            _rec("travel-pack", "travel", "Pack for a changeable evening", "Rain may affect destination plans", score,
                 [f"Rain probability is {weather.rain_probability}%", "The rain window begins in the evening"], "Carry rain protection", "Destination advice"),
            _rec("travel-window", "travel", "Complete outdoor plans earlier", "Conditions are more predictable before 4 PM", score-5,
                 ["Rain and wind increase later"], "Keep evening plans flexible", "Best time"),
            _rec("travel-visibility", "travel", "Check visibility before departure", f"Current visibility is {weather.visibility} km", score-12,
                 ["Visibility can change during showers"], "Review official warnings before travel", "Travel check"),
        ],
        Persona.COMMUTER: [
            _rec("commute-window", "commuter", "Rain may affect your evening commute", "Your usual route overlaps the likely rain window", score,
                 [f"Rain probability is {weather.rain_probability}%", f"Saved commute time is {profile.commute_time or '5:30 PM'}"], "Travel before 4:30 PM where possible", "Smart commute"),
            _rec("commute-two-wheeler", "commuter", "Two-wheeler conditions may become risky", "Rain and stronger wind are expected later", score-4,
                 ["Wet-road and crosswind conditions may overlap"], "Keep an alternate travel option ready", "Ride alert"),
            _rec("commute-visibility", "commuter", "Visibility check", f"Visibility is {weather.visibility} km", score-14,
                 ["Rain can reduce local visibility"], "Allow additional travel time", "Route context"),
        ],
        Persona.OUTDOOR_WORKER: [
            _rec("worker-heat", "outdoor_worker", "Heat exposure risk increases from 12–4 PM", "Strenuous outdoor work becomes less suitable at midday", score,
                 [f"Feels like {weather.feels_like}°C", f"UV index is {weather.uv_index}", "Outdoor work increases exposure"], "Schedule a shaded break from 1–2 PM", "Work-risk alert"),
            _rec("worker-rain", "outdoor_worker", "Work disruption is possible this evening", "Rain and wind increase after 4:30 PM", score-5,
                 ["Rain and wind overlap outdoor tasks"], "Secure loose equipment and finish exposed work earlier", "Preventive action"),
            _rec("worker-lightning", "outdoor_worker", "Watch for lightning updates", f"Demo lightning probability is {weather.lightning_probability}%", score-10,
                 ["Outdoor profiles receive earlier lightning escalation"], "Move indoors if an official warning is issued", "Safety watch"),
        ],
        Persona.EVENT: [
            _rec("event-window", "event", "Outdoor event suitability is moderate", "Heat and UV may reduce attendee comfort", score,
                 ["Peak heat occurs in the afternoon", "Rain is possible later"], "Prefer a start time after 5:30 PM with a rain backup", "Event window"),
        ],
        Persona.HEALTH: [
            _rec("health-environment", "health", "Outdoor conditions may feel uncomfortable", "Heat, UV and air quality are elevated", score,
                 [f"AQI is {weather.aqi}", f"UV index is {weather.uv_index}"], "Consider reducing prolonged outdoor exposure", "Environmental context"),
        ],
        Persona.GENERAL: [
            _rec("general-action", "general", "Plan strenuous outdoor activity earlier", "Heat, UV and wind rise later today", score,
                 ["Morning conditions are more comfortable"], "Use the 6:00–8:00 AM window", "Today’s action"),
        ],
    }
    return sorted(options.get(p, options[Persona.GENERAL]), key=lambda item: item.score, reverse=True)[:3]


def alert_for(profile: UserProfile, weather: Weather, impact: Impact) -> Alert:
    persona = profile.persona
    if weather.lightning_probability >= 30 and persona in {Persona.OUTDOOR_WORKER, Persona.FITNESS, Persona.FAMILY}:
        return Alert(title="Severe thunderstorm conditions may approach", message="A demo storm cell may affect outdoor plans.", severity="Critical",
                     source="Demo severe-weather scenario", distance_km=12, eta_minutes=45,
                     actions=["Move indoors", "Avoid open areas", "Check the latest official IMD warning"])
    titles = {
        Persona.FITNESS: "Cycling conditions may become difficult",
        Persona.FAMILY: "Outdoor family plans need attention",
        Persona.AGRICULTURE: "Rain and wind planning alert",
        Persona.TRAVEL: "Destination weather may affect plans",
        Persona.COMMUTER: "Evening commute disruption possible",
        Persona.OUTDOOR_WORKER: "Heat and wind work-risk alert",
    }
    return Alert(title=titles.get(persona, "Weather conditions need attention"),
                 message="Strong wind, heat and the evening rain window overlap with your selected context.",
                 severity=impact.level, source="Mausam+ demo rule", actions=[recommendations_for(profile, weather, impact)[0].action])


def build_feed(profile: UserProfile, weather: Weather) -> Feed:
    impact = impact_for(profile, weather)
    recommendations = recommendations_for(profile, weather, impact)
    alert = alert_for(profile, weather, impact)
    hourly = [
        {"time":"6 AM","icon":"☀️","temp":25,"event":"Safer window"}, {"time":"9 AM","icon":"🌤️","temp":29,"event":"UV rising"},
        {"time":"12 PM","icon":"☀️","temp":33,"event":"Peak heat"}, {"time":"3 PM","icon":"💨","temp":34,"event":"Strong wind"},
        {"time":"6 PM","icon":"🌧️","temp":30,"event":"Rain window"},
    ]
    daily = [
        {"day":"Today","icon":"🌤️","high":weather.temperature,"low":25,"rain":weather.rain_probability},
        {"day":"Thu","icon":"🌧️","high":31,"low":24,"rain":75}, {"day":"Fri","icon":"🌤️","high":32,"low":25,"rain":35},
        {"day":"Sat","icon":"☀️","high":34,"low":26,"rain":15},
    ]
    observations = [CommunityObservation(id="obs-water-1", type="waterlogging", location="Near SG Highway", distance_km=1.8,
                                         reported_at="12 minutes ago", count=7)]
    return Feed(location={"name":profile.location,"label":"Active location"}, weather=weather, impact=impact,
                cards=recommendations, recommendations=recommendations, alerts=[alert],
                explanation={"title":"Why am I seeing this?","items":[f"You selected {profile.persona.value.replace('_',' ').title()}", *recommendations[0].reason],
                             "summary":"Weather, time, location and your context determine this priority."},
                hourly=hourly, daily=daily, observations=observations)


def recommendation(persona: Persona, weather: Weather) -> Recommendation:
    profile = UserProfile(persona=persona)
    return recommendations_for(profile, weather, impact_for(profile, weather))[0]
