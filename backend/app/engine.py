"""Versioned, explainable planning model. Scores are heuristics, not probabilities."""
from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256

from .schemas import Alert, Feed, Impact, Persona, Recommendation, UserProfile, Weather

MODEL_VERSION = "mausam-rules-2.0"
SUBJECTS = {
    "fitness": "outdoor exercise", "family": "family outdoor plans", "agriculture": "field work",
    "travel": "travel", "health": "outdoor exposure", "commuter": "your commute",
    "outdoor_worker": "outdoor work", "event": "your outdoor event", "general": "your daily plans",
    "beach": "coastal outdoor plans",
}
ACTIONS = {
    "Temperature": "Reduce strenuous exposure and plan shaded breaks",
    "Rain": "Carry rain protection and keep a covered alternative",
    "UV": "Use shade and sun protection during the indicated period",
    "Air quality": "Consider reducing prolonged outdoor exertion",
    "Humidity": "Allow more rest time during warm, humid outdoor activity",
    "Wind": "Secure loose items and reassess exposed outdoor activity",
    "Visibility": "Allow extra travel time and check local travel conditions",
    "Lightning": "Move into a substantial building if thunder is heard",
    "Flooding": "Avoid flooded roads and follow local official instructions",
    "Fog": "Allow extra travel time in reduced visibility",
    "Dust": "Reduce exposure to blowing dust and check air-quality updates",
    "Cyclone": "Follow the official cyclone bulletin and local instructions",
}


def priority(score: int) -> str:
    return "Critical" if score >= 85 else "High" if score >= 60 else "Moderate" if score >= 30 else "Low"


def context_weights(profile: UserProfile) -> dict[str, float]:
    weights = dict.fromkeys(ACTIONS, 1.0)
    selected = {
        Persona.FITNESS: ("Temperature", "UV", "Wind"),
        Persona.FAMILY: ("Temperature", "UV", "Rain"),
        Persona.AGRICULTURE: ("Rain", "Wind", "Humidity"),
        Persona.TRAVEL: ("Rain", "Visibility", "Fog"),
        Persona.COMMUTER: ("Rain", "Visibility", "Wind"),
        Persona.OUTDOOR_WORKER: ("Temperature", "Humidity", "Lightning"),
        Persona.HEALTH: ("Air quality", "Dust", "Temperature"),
        Persona.EVENT: ("Rain", "Wind", "Temperature"),
        Persona.BEACH: ("Wind", "Cyclone", "Lightning"),
    }.get(profile.persona, ())
    for name in selected:
        weights[name] += .35
    # Match meaning, never increase risk just because more preferences were entered.
    activity_map = {
        "cycling": ("Wind", "Temperature"), "walking": ("UV", "Temperature"),
        "school commute": ("Rain", "Visibility"), "farming": ("Rain", "Wind"),
        "gardening": ("UV", "Rain"), "outdoor work": ("Temperature", "Humidity"),
        "travel": ("Rain", "Visibility"), "outdoor events": ("Rain", "Wind"),
    }
    for name in {factor for item in profile.activities for factor in activity_map.get(item.casefold(), ())}:
        weights[name] += .15
    if profile.extra_protection:
        for name in ("Temperature", "Air quality", "UV"):
            weights[name] += .2
    return weights


def measurements(weather: Weather) -> dict[str, tuple[int, str]]:
    w = weather
    # Bounded planning thresholds; unavailable official hazards receive no invented evidence.
    scale = lambda value, start, width: max(0, min(100, round((value - start) / width * 100)))
    result = {
        "Temperature": (max(scale(w.feels_like, 28, 17), scale(5 - w.temperature, 0, 20)), f"Feels like {w.feels_like}°C; temperature {w.temperature}°C"),
        "Rain": (scale(w.rain_probability, 20, 70), f"Rain probability {w.rain_probability}%"),
        "UV": (scale(w.uv_index, 2, 9), f"UV index {w.uv_index}"),
        "Air quality": (scale(w.aqi, 50, 150) if w.aqi is not None else 0, f"US AQI {w.aqi}" if w.aqi is not None else "AQI unavailable"),
        "Humidity": (scale(w.humidity, 65, 30) if w.feels_like >= 30 else 0, f"Humidity {w.humidity}% with feels-like {w.feels_like}°C"),
        "Wind": (scale(w.wind_speed, 15, 45), f"Wind {w.wind_speed} km/h"),
        "Visibility": (scale(5 - w.visibility, 0, 5), f"Visibility {w.visibility} km"),
        "Lightning": (90 if w.thunderstorm else 0, "Thunderstorm weather code present" if w.thunderstorm else "No thunderstorm signal in this snapshot; lightning probability unavailable"),
        "Flooding": (0, "Official flood assessment unavailable"),
        "Fog": (65 if "fog" in w.condition.casefold() else 0, f"Condition: {w.condition}"),
        "Dust": (45 if w.dust_risk == "moderate" else 0, f"Dust indicator: {w.dust_risk}"),
        "Cyclone": (0, "Official cyclone assessment unavailable"),
    }
    if w.severe_data_available:
        result["Flooding"] = (90 if w.flood_risk == "high" else 40 if w.flood_risk == "moderate" else 0, f"Source flood risk: {w.flood_risk}")
        result["Cyclone"] = (100 if w.cyclone_risk == "warning" else 65 if w.cyclone_risk == "watch" else 0, f"Source cyclone status: {w.cyclone_risk}")
    return result


def impact_for(profile: UserProfile, weather: Weather) -> Impact:
    weights = context_weights(profile)
    values = measurements(weather)
    # Independent contributions sum exactly to the displayed capped score.
    contributions = {name: round(severity * weights[name] / 5) for name, (severity, _) in values.items()}
    total = sum(contributions.values())
    if total > 100:
        scaled = {name: int(value * 100 / total) for name, value in contributions.items()}
        for name in sorted(contributions, key=contributions.get, reverse=True)[:100-sum(scaled.values())]:
            scaled[name] += 1
        contributions = scaled
    factors = [{"name": name, "status": priority(raw), "contribution": contributions[name],
                "explanation": f"{detail}; relevance multiplier {weights[name]:.2f} for {profile.persona.value.replace('_', ' ')}"}
               for name, (raw, detail) in values.items()]
    factors.sort(key=lambda f: f["contribution"], reverse=True)
    score = sum(contributions.values())
    return Impact(score=score, level=priority(score), factors=factors)


def _snapshot(base: Weather, row: dict) -> Weather:
    updates = {}
    for key, field in {"temp": "temperature", "feels_like": "feels_like", "humidity": "humidity",
                       "rain": "rain_probability", "wind": "wind_speed", "uv": "uv_index",
                       "visibility": "visibility"}.items():
        if row.get(key) is not None:
            updates[field] = row[key]
    # AQI remains explicitly the current-context reading, not an hourly prediction.
    code = row.get("weather_code")
    if code is not None:
        updates.update(thunderstorm=code in (95, 96, 99), condition=str(row.get("event", base.condition)))
    return base.model_copy(update=updates)


def _periods(weather: Weather, hourly: list[dict]) -> list[tuple[Weather, str, float, dict]]:
    periods = [(weather, "Current conditions", 0.0, {})]
    for row in hourly:
        if "timestamp" not in row:
            continue
        hours = float(row.get("hours_ahead", 0))
        if not 0 <= hours <= 24:
            continue
        periods.append((_snapshot(weather, row), str(row["time"]), hours, row))
    return periods


def _routine_overlap(profile: UserProfile, row: dict) -> bool:
    if not profile.commute_time or not row.get("timestamp"):
        return False
    try:
        routine = datetime.strptime(profile.commute_time, "%H:%M")
        stamp = datetime.fromisoformat(str(row["timestamp"]))
        return abs((stamp.hour * 60 + stamp.minute) - (routine.hour * 60 + routine.minute)) <= 60
    except ValueError:
        return False


def evaluate(profile: UserProfile, weather: Weather, hourly: list[dict]) -> tuple[Impact, list[Recommendation], list[Alert]]:
    periods = _periods(weather, hourly)
    weights = context_weights(profile)
    subject = SUBJECTS[profile.persona.value]
    context = f"Your context: {subject}; activities: {', '.join(profile.activities) or 'none selected'}"
    if profile.extra_protection:
        context += "; protection: " + ", ".join(profile.extra_protection)
    if profile.routine:
        context += "; daily needs: " + profile.routine
    if profile.commute_time:
        context += f"; departure {profile.commute_time}"
    candidates = []
    alerts = []
    for hazard in ACTIONS:
        scored = []
        for snapshot, label, hours, row in periods:
            raw, detail = measurements(snapshot)[hazard]
            timing = 1 if hours <= 6 else .85
            overlap = _routine_overlap(profile, row)
            relevance = weights[hazard] + (.2 if overlap else 0)
            rank = min(100, round(raw * relevance * timing))
            scored.append((rank, raw, detail, label, hours, overlap))
        rank, raw, detail, label, hours, overlap = max(scored, key=lambda x: x[0])
        if raw < 25:
            continue
        reasons = [detail, context, f"{weather.location}: {label}; forecast horizon {round(hours)}h",
                   f"Priority {rank}/100 = condition {raw} × relevance {weights[hazard] + (.2 if overlap else 0):.2f} × timing {1 if hours <= 6 else .85} (capped)"]
        if overlap:
            reasons.append(f"Forecast overlaps your {profile.commute_time} departure")
        slug = hazard.lower().replace(" ", "-")
        action = ACTIONS[hazard]
        if hazard == "Rain" and profile.persona == Persona.AGRICULTURE:
            action = "Review field-work timing; use an official agromet advisory for irrigation decisions"
        if hazard == "Wind" and profile.persona == Persona.FITNESS:
            action = "Reassess exposed cycling routes and choose a sheltered alternative"
        candidates.append(Recommendation(id=slug, type=profile.persona.value,
            title=f"{hazard} planning for {subject}", message=f"{label} in {weather.location}: {detail.lower()}.",
            priority=priority(rank), score=rank, reason=reasons, action=action, badge="Preventive guidance"))
        if raw >= 45:
            # Stable within a local forecast day: refreshes do not generate duplicate notifications.
            day = next((str(row.get("timestamp", ""))[:10] for _, _, _, row in periods if row.get("timestamp")), datetime.now().date().isoformat())
            alert_id = sha256(f"{weather.location.casefold()}:{hazard}:{priority(raw)}:{day}".encode()).hexdigest()[:20]
            demo = "demo" in weather.source.casefold()
            alerts.append(Alert(id=alert_id, title=f"{hazard}: {subject}", message=f"{detail}. {label} in {weather.location}.",
                severity=priority(raw), source="Demo scenario" if demo else "Mausam+ generated guidance",
                source_type="demo" if demo else "generated", actions=[action], reason=reasons, rank=rank,
                location=weather.location, valid_at=label,
                notification_eligible=profile.notifications_enabled and not demo and raw >= 60 and rank >= 60 and hours <= 6))
    # Select a future, daylight interval using the same weighted risks.
    windows = [(snapshot, label, row) for snapshot, label, hours, row in periods if row and row.get("is_day") == 1 and hours >= 0]
    if windows:
        best, label, row = min(windows, key=lambda item: max(raw * weights[name] for name, (raw, _) in measurements(item[0]).items()))
        worst = max(raw * weights[name] for name, (raw, _) in measurements(best).items())
        suitable = worst < 60
        window_reason = [context, f"Compared {len(windows)} upcoming daylight forecast hours using the same risk factors",
            f"{label}: feels like {best.feels_like}°C, rain {best.rain_probability}%, UV {best.uv_index}, wind {best.wind_speed} km/h",
            "Relative planning guidance; conditions can change"]
        candidates.append(Recommendation(id="activity-window", type=profile.persona.value,
            title=f"{'Lower-exposure period' if suitable else 'No low-risk period found'} for {subject}",
            message=f"{label} has the lowest combined exposure among the available daylight forecast hours.",
            priority="Low" if suitable else "Moderate", score=25 if suitable else 50, reason=window_reason,
            action=f"Consider {label} for {subject}" if suitable else "Keep a sheltered alternative; even the best interval has elevated exposure",
            badge="Activity timing"))
    if not candidates:
        candidates.append(Recommendation(id="routine", type=profile.persona.value, title=f"Briefing for {subject}",
            message=f"No elevated planning thresholds in the available data for {weather.location}.",
            priority="Low", score=0, reason=[context, "Available temperature, rain, UV, air quality, humidity, wind and visibility thresholds checked"],
            action="Check the forecast again before your activity", badge="Daily guidance"))
    # A data-gap action is always available; it never claims an official warning.
    candidates.append(Recommendation(id="source-check", type=profile.persona.value, title="Check official severe-weather warnings",
        message="Official IMD warnings are not connected to this deployment.",
        priority="Low", score=0, reason=[weather.source, "Flood, cyclone, and lightning probabilities cannot be inferred from rain probability"],
        action="Consult the latest IMD bulletin before weather-sensitive decisions", badge="Source status"))
    candidates.sort(key=lambda item: item.score, reverse=True)
    alerts.sort(key=lambda item: ({"Critical": 3, "High": 2, "Moderate": 1, "Low": 0}[item.severity], item.rank), reverse=True)
    return impact_for(profile, weather), candidates[:3], alerts


def recommendations_for(profile: UserProfile, weather: Weather, impact: Impact) -> list[Recommendation]:
    return evaluate(profile, weather, [])[1]


def build_feed(profile: UserProfile, weather: Weather, hourly_data: list[dict] | None = None,
               daily_data: list[dict] | None = None) -> Feed:
    hourly, daily = hourly_data or [], daily_data or []
    impact, recs, alerts = evaluate(profile, weather, hourly)
    gaps = ["Official IMD warnings are not connected; flood and cyclone assessments unavailable."]
    if weather.aqi is None:
        gaps.append("AQI is unavailable for this update.")
    return Feed(location={"name": weather.location, "label": "Active location"}, weather=weather, impact=impact,
        cards=recs, recommendations=recs, alerts=alerts, notifications=[a for a in alerts if a.notification_eligible],
        notifications_enabled=profile.notifications_enabled, model_version=MODEL_VERSION, data_gaps=gaps,
        explanation={"title": "Why am I seeing this?", "items": recs[0].reason,
                     "summary": "Measured conditions × persona and activity relevance × timing determine priority."},
        hourly=hourly, daily=daily, observations=[], is_demo_data="demo" in weather.source.lower(), provider=weather.source)


def recommendation(persona: Persona, weather: Weather) -> Recommendation:
    return evaluate(UserProfile(persona=persona), weather, [])[1][0]
