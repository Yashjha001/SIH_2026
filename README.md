# Mausam+

**Weather that understands your day.** Mausam+ is a Smart India Hackathon MVP that puts a transparent personalization layer on top of weather data. It demonstrates the core story: **same weather → different people → different intelligence**.

## What is included

- Responsive React + TypeScript application with a polished landing page and personalized dashboard.
- Guided onboarding for location, persona, activities, routine, and optional protection needs.
- Deep demo switcher for Fitness, Family, Agriculture/Gardening, and Traveler contexts, plus working Commuter, Outdoor Worker, Health, Events, and General profiles.
- FastAPI REST API with Pydantic validation and automatic OpenAPI documentation.
- Live Open-Meteo current conditions, hourly forecast, seven-day forecast, AQI, UV, and global location search, with a five-minute cache and a clearly labelled safe fallback.
- Deterministic, explainable recommendation and alert rules with visible factor contributions. No medical claims or fabricated official advisories.
- Three ranked preventive actions, routine-aware commute guidance, severe-event distance/arrival context, and clearly separated community observations.
- Current conditions, hourly timeline, daily outlook, impact heuristic, transparent explanations, and location switching.

## Architecture

```text
React UI → FastAPI endpoints → Personalization / recommendation rules → WeatherProvider
                                                               ├── OpenMeteoWeatherProvider (live)
                                                               └── MockWeatherProvider (network fallback)
```

The provider interface remains separated so an approved IMD source can be integrated later without changing the UI or rule engine. Live weather is refreshed by the UI every five minutes and whenever the browser regains focus.

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

## Deploy to Vercel and Render

1. Create a Render **Web Service** from this repository. The included `render.yaml` can be used as a Blueprint, or configure these values manually:
    - Root directory: `backend`
    - Build command: `pip install -r requirements.txt`
    - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
    - Health check path: `/api/health`
2. Copy the Render service URL, for example `https://mausam-plus-api.onrender.com`.
3. Import the repository into Vercel. The included `vercel.json` configures `npm ci`, `npm run build`, the `dist` output, and SPA routing.
4. Add this Vercel environment variable for **Production** (and Preview if needed):
    - `VITE_API_URL=https://mausam-plus-api.onrender.com`
5. Set the Render environment variable `CORS_ORIGINS` to the Vercel deployment URL, for example `https://mausam-plus.vercel.app`. For multiple origins, separate URLs with commas.
6. Redeploy both services after saving the environment variables, then verify `/api/health` on Render and the Vercel site.

The frontend uses the local Vite proxy when `VITE_API_URL` is unset, so local development remains unchanged.

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
- `GET/POST /api/community/observations`

## Personalization engine

The engine uses deterministic MVP heuristics. It combines persona relevance and protection preferences with temperature, UV, rain, wind, air quality, location, and routine. It returns three ranked actions, a factor-by-factor impact score, a relevant alert, and a human-readable explanation. The score is a **Personalized Weather Impact** heuristic, not an official weather, health, or safety classification.

This personalization layer is **not a trained machine-learning model**, so it must not be described as one. Weather prediction comes from Open-Meteo's numerical weather-prediction sources; Mausam+ applies tested, explainable rules on top. Training a separate ML risk model responsibly requires a versioned historical dataset, ground-truth outcomes, leakage checks, offline evaluation, calibration, and monitoring. Synthetic demo data is not used to create a misleading “trained” claim. Runtime status is available at `GET /api/model/status`.

## Limitations and next steps

This release does not claim a live IMD integration. Before public deployment, use a durable database/repository layer for users and locations, configure CORS through environment variables, add authenticated accounts, and complete provider licensing/attribution review for the intended traffic level.
