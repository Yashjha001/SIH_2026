# Mausam+

**Weather that understands your day.** Mausam+ is a Smart India Hackathon MVP that puts a transparent personalization layer on top of weather data. It demonstrates the core story: **same weather → different people → different intelligence**.

## What is included

- Responsive React + TypeScript application with a polished landing page and personalized dashboard.
- Instant demo switcher for Fitness, Family, Agriculture/Gardening, and Traveler contexts.
- FastAPI REST API with Pydantic validation and automatic OpenAPI documentation.
- Configurable mock weather provider; all data is visibly labelled as demo data.
- Deterministic, explainable recommendation and alert rules. No medical claims or fabricated official advisories.
- Current conditions, hourly timeline, daily outlook, impact heuristic, transparent explanations, and location switching.

## Architecture

```text
React UI → FastAPI endpoints → Personalization / recommendation rules → WeatherProvider
                                                               └── MockWeatherProvider (MVP)
```

The provider interface is intentionally separated so an approved IMD or other weather data source can be integrated later without changing the UI or rule engine.

## Run locally

Prerequisites: Node.js 20+ and Python 3.11+.

```powershell
# Terminal 1 — API
cd C:\SIH_YASH\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```powershell
# Terminal 2 — web application
cd C:\SIH_YASH
npm install
npm run dev
```

Open `http://localhost:5173`. API documentation is at `http://127.0.0.1:8000/docs`.

## Testing and production build

```powershell
cd C:\SIH_YASH\backend
python -m pytest

cd C:\SIH_YASH
npm run build
```

## API highlights

- `GET /api/health`
- `GET /api/weather/current?location=Ahmedabad`
- `GET /api/users/demo-user/personalized-feed?persona=fitness&location=Ahmedabad`
- `GET/PUT /api/users/{id}`
- `GET/POST /api/users/{id}/locations`
- `GET /api/demo/scenarios` and `POST /api/demo/scenarios/{scenario_id}`

## Personalization engine

The engine uses deterministic MVP heuristics. It combines persona relevance with temperature/UV, rain probability, and wind, then returns a prioritised recommendation, impact score, alert, and a human-readable explanation. The score is a **Personalized Weather Impact** heuristic, not an official weather, health, or safety classification.

## Limitations and next steps

This release uses deliberately fixed mock scenarios and does not claim a live IMD integration. Before deployment, integrate an approved provider behind `WeatherProvider`, use a durable database/repository layer for users and locations, configure CORS/secrets through environment variables, and add authenticated user accounts.
