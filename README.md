# AI-DERS

**AI-Driven Disaster Evacuation & Emergency Response System**  
*Intelligent emergency response under uncertainty.*

> **Academic simulation only.** AI-DERS is a student project for demonstrating AI techniques in a simulated disaster environment. It is not an operational emergency-management system, and its outputs must not be used to make real emergency decisions.

## Live Demo

- **Frontend:** https://ai-ders-frontend.onrender.com
- **Backend API:** https://ai-ders-backend.onrender.com
- **API health check:** https://ai-ders-backend.onrender.com/api/health
- **Interactive API documentation:** https://ai-ders-backend.onrender.com/docs
- **GitHub repository:** https://github.com/theskymishra/AI-PROJECT

The frontend is deployed separately from the FastAPI backend on Render. The frontend uses `VITE_API_URL` to connect to the backend.

> **Free hosting note:** Render free services may take a little time to respond after a period of inactivity. The simulation state is held in backend memory, so it can reset when the backend restarts or redeploys.

## Overview

AI-DERS demonstrates how AI techniques can support evacuation routing and emergency-response decisions when conditions are uncertain and can change over time. A simulated world contains roads, zones, shelters, hospitals, ambulances, emergencies, and changing flood conditions. Sensor observations feed probabilistic reasoning; inferred road-failure risk is then used by the route planner.

The project combines a deterministic simulation engine, an interactive disaster map, AI-based route search, probabilistic inference, and a web dashboard.

## Features

### Simulation and monitoring
- Deterministic, tick-based simulation (one tick represents one simulated second).
- A simulated world with 24 nodes, 38 roads, and 5 zones.
- Scenarios: `NORMAL`, `MODERATE_FLOOD`, `SEVERE_FLOOD`, and `DYNAMIC_ROAD_FAILURE`.
- Start, pause, resume, reset, simulation-speed controls, and scenario selection.
- Live environment information, event timeline, alerts, and dashboard status.
- Server-Sent Events (SSE) for live updates, including sequence-gap resynchronisation.

### Interactive disaster map
- SVG map with zoom, pan, hover highlighting, and click-to-inspect details.
- Visualisation of zones, roads, hospitals, shelters, ambulances, emergencies, and flood conditions.
- Road status indicators for `SAFE`, `RISKY`, and `BLOCKED` roads.
- Map available in both an interactive view and a dashboard embed.

### AI routing and probabilistic reasoning
- A* search implementation for disaster-aware route planning.
- Route costs account for distance and inferred road-failure probability.
- A* optimality was verified against Floyd–Warshall for all 552 ordered node pairs.
- Hidden Markov Model (HMM) uses noisy sensor observations to estimate hidden flood severity.
- Bayesian Network estimates road-failure probability, using HMM belief as virtual evidence.
- Noisy-OR model for road-failure probability.
- Risk Analysis interface with belief visualisations, belief-over-time chart, network diagram, and sensor charts.
- API endpoints for route search, HMM inference, and Bayesian inference.
- Knowledge reasoning, constraint satisfaction, planning, real-time event handling, analytics, testing, and final integration are included in the 14-phase project.

## AI pipeline

The core probabilistic routing flow is:

1. The simulation produces sensor observations and environmental state.
2. The HMM updates its belief about flood severity from noisy observations.
3. The Bayesian Network combines evidence to estimate road-failure probability.
4. The route planner uses the inferred risk as part of its edge cost.
5. When the environment changes, routes can be recalculated against the updated state.

The routing cost uses the inferred road-failure probability as its risk input rather than independently adding the same underlying flood and damage evidence a second time.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI, Uvicorn |
| Backend validation and data models | Pydantic |
| Frontend | React, TypeScript, Vite |
| Frontend testing | Vitest, jsdom |
| Backend testing | pytest |
| Live updates | Server-Sent Events (SSE) |
| Deployment | Render |

AI-DERS does not require a GPU, a database, Docker, or external AI APIs for the local simulation.

## Requirements

- Python 3.11 or newer (developed and tested with Python 3.12)
- Node.js 20 or newer (developed and tested with Node.js 22)
- macOS (Apple Silicon or Intel) or Windows 10/11
- Git

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/theskymishra/AI-PROJECT.git
cd AI-PROJECT
```

### 2. Set up the backend

**macOS / Linux**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

**Windows PowerShell**
```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks virtual-environment activation, allow it for the current session only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 3. Start the backend

From the `backend` directory, with the virtual environment activated:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend will be available at:

- API base: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

**Important:** Run exactly one backend worker. The simulation state is held in process memory; multiple workers would create separate simulation states. Do not use `--workers` or set `WEB_CONCURRENCY` above `1`.

### 4. Set up the frontend

Open a second terminal from the repository root.

**macOS / Linux**
```bash
cd frontend
npm install
cp .env.example .env
```

**Windows PowerShell**
```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

### 5. Start the frontend

From the `frontend` directory:

```bash
npm run dev
```

Open http://localhost:5173.

The local frontend configuration should point to the local backend:

```dotenv
VITE_API_URL=http://localhost:8000
```

If you change the frontend origin or backend URL, ensure the backend CORS configuration allows that frontend origin.

## Configuration

### Backend: `backend/.env`

| Variable | Default | Purpose |
|---|---|---|
| `AIDERS_HOST` | `127.0.0.1` | Default interface for the backend |
| `AIDERS_PORT` | `8000` | Default backend port |
| `AIDERS_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed browser origins |
| `AIDERS_SEED` | `20260828` | Master simulation seed |

### Frontend: `frontend/.env`

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Base URL of the backend API |

`VITE_API_URL` is read in `frontend/src/config.ts`. Keep the backend URL configuration in this file rather than hard-coding URLs throughout the frontend.

## Deployment on Render

The project uses two Render services: a backend web service and a frontend static site.

### Backend service

- **Root directory:** `backend`
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment variables:**
  - `AIDERS_SEED=20260828`
  - `AIDERS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://ai-ders-frontend.onrender.com`
  - `WEB_CONCURRENCY=1` (keep a single worker for the in-memory simulation)

### Frontend static site

- **Root directory:** `frontend`
- **Build command:** `npm install && npm run build`
- **Publish directory:** `dist`
- **Environment variable:**
  - `VITE_API_URL=https://ai-ders-backend.onrender.com`

After changing environment variables, redeploy the relevant service. The frontend origin must be included in the backend's `AIDERS_CORS_ORIGINS` value.

### Automatic deployments

If **Auto-Deploy** is enabled for a service in Render, pushing to its configured branch triggers a new deployment. The services are configured separately, so backend changes deploy the backend and frontend changes deploy the frontend.

Typical workflow:

```bash
git add .
git commit -m "Describe your changes"
git push origin main
```

Check each service's **Settings → Build & Deploy → Auto-Deploy** setting in Render if a push does not trigger a deployment.

## Testing

Run the tests from the relevant project directory.

### Backend

```bash
cd backend
# Activate .venv first
python -m pytest
```

The latest recorded local test run passed **477 backend tests**. If your branch has changed since that run, execute the suite again to confirm the current result.

### Frontend

```bash
cd frontend
npm install
npm run typecheck
npm test
npm run build
```

The frontend production build runs TypeScript checking, the Vitest test suite, and Vite's production build. The latest recorded deployment build passed **98 frontend tests**.

### Integration checks

With both local servers running, the repository includes these verification scripts:

```bash
node scripts/verify_contract.mjs
./scripts/verify_sse.sh
```

These check live API/SSE behaviour in addition to unit tests. Run them from the repository root.

## Project Structure

```text
AI-PROJECT/
├── backend/
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── ai/
│       │   ├── search/
│       │   └── probability/
│       ├── api/
│       ├── models/
│       └── tests/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── config.ts
│       ├── types/
│       ├── services/
│       ├── hooks/
│       ├── components/
│       └── pages/
└── scripts/
    ├── verify_contract.mjs
    └── verify_sse.sh
```

The backend's Pydantic models in `backend/app/models/` and the matching TypeScript types in `frontend/src/types/index.ts` form a shared data contract. When changing a shared model, update both sides in the same commit and coordinate the change with the team.

## Phase Roadmap

All 14 project phases are complete in the current deployed build.

| Phase | Focus | Status |
|---|---|---|
| 1 | Foundation and shared data contract | Complete |
| 2 | Simulation core, tick clock, and SSE | Complete |
| 3 | Interactive disaster map | Complete |
| 4 | A* routing and route cache | Complete |
| 5 | HMM and Bayesian Network probabilistic reasoning | Complete |
| 6 | Knowledge engine, forward chaining, and first-order logic | Complete |
| 7 | Constraint satisfaction and resource allocation | Complete |
| 8 | Classical and hierarchical planning | Complete |
| 9 | Full pipeline integration and automatic replanning | Complete |
| 10 | Real-time event engine | Complete |
| 11 | UI polish | Complete |
| 12 | Analytics | Complete |
| 13 | Testing and hardening | Complete |
| 14 | Documentation, final integration, and demo | Complete |

## Troubleshooting

**Dashboard shows Offline**
- Confirm the backend is running.
- Open `http://localhost:8000/api/health` to check backend availability.
- Confirm `VITE_API_URL` points to the correct backend.
- Ensure `AIDERS_CORS_ORIGINS` includes the exact frontend origin, including protocol and port.

**CORS errors**
- `localhost` and `127.0.0.1` are different browser origins.
- Add the exact frontend origin to `AIDERS_CORS_ORIGINS`, then restart or redeploy the backend.

**Vite reports that port 5173 is in use**
- Stop the process using the port, or configure a different frontend port and allow that origin in backend CORS settings.

**`uvicorn` is not found**
- Activate the backend virtual environment and install dependencies with `pip install -r requirements.txt`.

**Frontend changes do not appear on Render**
- Confirm the changes are committed and pushed to the branch configured for the frontend service.
- Confirm Auto-Deploy is enabled and check the latest Render build logs.
- Remember that `VITE_API_URL` is applied at build time, so changes to it require a new frontend build/deployment.

**Backend is slow on the first request**
- A free Render service may be waking after inactivity. Allow time for it to start, then retry the health endpoint.

## Project Disclaimer

AI-DERS is developed for educational and demonstration purposes. Its simulated environment, model assumptions, data, and route recommendations do not represent verified real-world emergency conditions. Do not rely on it for actual evacuation, rescue, medical, or emergency-management decisions.
