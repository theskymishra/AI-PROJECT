# AI-DERS

**AI-Driven Disaster Evacuation & Emergency Response System**
*Intelligent emergency response under uncertainty.*

> **This is an academic AI simulation.** It is not an operational
> emergency-management system. No output it produces should be used to make real
> emergency decisions.

**Current build: Phase 2 of 14 — Disaster Simulation Core.**

---

## What exists right now

Phases 1 and 2. There is no AI yet — search, CSP, probabilistic reasoning and
planning arrive in Phases 4 through 8. What works today:

**Phase 2 — simulation core**

- Deterministic tick-based simulation engine (1 tick = 1 simulated second)
- 24-node / 38-road / 5-zone world with three distinct Riverside→Highland corridors
- Four scenarios: NORMAL, MODERATE_FLOOD, SEVERE_FLOOD, DYNAMIC_ROAD_FAILURE
- Hidden true flood state with noisy sensor emission (the Phase 5 HMM inverts this)
- Start / pause / resume / reset / speed (1x, 2x, 5x) / scenario selection
- Server-Sent Events push with sequence-gap resynchronisation
- Live dashboard: stats, world overview, environment, event timeline, alerts
- `environment_version` route-cache invalidation with RISK_EPSILON change detection

**Phase 1 — foundation**

- FastAPI backend with a health endpoint and configured CORS
- React + TypeScript + Vite frontend with the dark command-centre design system
- Application shell: sidebar, header, dashboard
- Live backend connection monitoring with specific, actionable error states
- The **frozen data contract**: Pydantic models and their TypeScript mirror
- The deterministic `patients` derivation rule, with tests
- 255 backend tests

The dashboard shows connection status and backend build information — the things
that are genuinely real at this stage. There are deliberately no statistic cards
reading `0` or `--`; a number with nothing behind it teaches you to distrust the
numbers that will be real later.

---

## Requirements

| | |
|---|---|
| Python | 3.11 or newer (developed against 3.12) |
| Node.js | 20 or newer (developed against 22) |
| OS | macOS (Apple Silicon or Intel) and Windows 10/11 |

No Docker. No GPU. No database. No external AI APIs. Everything runs locally.

---

## Installation

Clone or unpack the project, then set up each half once.

### Backend

**macOS / Linux**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

**Windows (Command Prompt)**

```bat
cd backend
py -3 -m venv .venv
.venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

> If PowerShell refuses to run the activate script, allow it for the current
> session only:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### Frontend

Identical on all platforms except the file copy.

**macOS / Linux**

```bash
cd frontend
npm install
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

**Windows (Command Prompt)**

```bat
cd frontend
npm install
copy .env.example .env
```

---

## Running

Two terminals. Backend first.

### Terminal 1 — backend

**macOS / Linux**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Windows (PowerShell)**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Windows (Command Prompt)**

```bat
cd backend
.venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000
```

> **Run exactly one worker.** From Phase 2 the entire simulation lives in memory
> in a single process. Multiple workers produce multiple divergent simulations
> with clients randomly attached to each. Never pass `--workers`, and do not set
> `WEB_CONCURRENCY` above 1. The backend logs a warning if it detects otherwise.

Backend: <http://localhost:8000>
Interactive API docs: <http://localhost:8000/docs>

### Terminal 2 — frontend

All platforms:

```bash
cd frontend
npm run dev
```

Frontend: <http://localhost:5173>

---

## Testing

### Backend

```bash
cd backend
# activate the virtualenv first (see above)
python -m pytest
```

Expected: `255 passed`.

Warnings are promoted to errors (`-W error` in `pytest.ini`). A warning nobody
fixes is a warning everybody learns to ignore, and that is how a real one gets
missed.

Useful variations:

```bash
python -m pytest -v                                   # per-test names
python -m pytest app/tests/unit/test_patients_rule.py # one file
```

### Frontend

```bash
cd frontend
npm run typecheck    # tsc --noEmit
npm run build        # typecheck, then production build
```

### Integration (both servers must be running)

```bash
node scripts/verify_contract.mjs   # 54 live API + SSE contract checks
./scripts/verify_sse.sh            # SSE headers, frames, subscriber cleanup
```

These exist because a green build and a clean typecheck proved nothing about
whether live state actually reaches a client. Two real defects — an
intermittently-absent SSE field, and partial road deltas being replaced rather
than merged — passed both and were caught only here.

`npm run build` runs the typecheck first, so a type error fails the build rather
than shipping.

---

## Verifying the installation

With both servers running:

1. Open <http://localhost:5173>. The dashboard should show **Online** with a
   round-trip figure in milliseconds.
2. Stop the backend (Ctrl+C). Within 15 seconds the badge turns **Offline** and
   the dashboard explains what to check.
3. Restart the backend and press **Re-check**. It returns to **Online**.

Direct backend check:

```bash
curl http://localhost:8000/api/health
```

---

## Configuration

Neither `.env` file is required — both halves have working defaults — but
copying the examples makes the configuration explicit.

`backend/.env`

| Variable | Default | Purpose |
|---|---|---|
| `AIDERS_HOST` | `127.0.0.1` | Interface uvicorn binds to |
| `AIDERS_PORT` | `8000` | Backend port |
| `AIDERS_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed browser origins |
| `AIDERS_SEED` | `20260828` | Master simulation seed |

`frontend/.env`

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL |

`VITE_API_URL` is read in exactly one place, `frontend/src/config.ts`. Nothing
else in the frontend may reference a backend URL directly.

---

## Project layout

```
ai-ders/
├── backend/
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   └── app/
│       ├── main.py            app factory, CORS, lifespan
│       ├── config.py          every tuning constant, one place
│       ├── api/health.py      the only endpoint in Phase 1
│       ├── models/            FROZEN CONTRACT — Pydantic
│       └── tests/unit/        60 tests
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── .env.example
    └── src/
        ├── main.tsx
        ├── App.tsx            route table
        ├── index.css          design tokens
        ├── config.ts          the only place VITE_API_URL is read
        ├── types/index.ts     FROZEN CONTRACT — TypeScript mirror
        ├── services/api.ts    axios client, error normalisation
        ├── hooks/             useBackendHealth
        ├── components/layout/ AppLayout, Sidebar, Header, StatusBadge, routes
        └── pages/Dashboard.tsx
```

### The frozen contract

`backend/app/models/` and `frontend/src/types/index.ts` describe the same
shapes. **They must change in the same commit**, agreed by all three team
members. Agreement is enforced by review rather than by tooling — a deliberate
trade-off, since schema-generation tooling would be a fourth thing to maintain
on a three-person project.

Most of those types have no consumer yet. That is the point: freezing the
contract in Phase 1 is what lets frontend work proceed in parallel with backend
work instead of waiting for it.

---

## Design system

Five semantic colours and no sixth:

| Token | Hex | Meaning |
|---|---|---|
| `info` | `#3B82F6` | system / AI activity |
| `safe` | `#10B981` | safe / success |
| `warn` | `#F59E0B` | warning / strained |
| `crit` | `#EF4444` | critical / blocked |
| `idle` | `#6B7280` | inactive / neutral |

The default Tailwind palette is **reset** in `src/index.css`. `bg-blue-500` and
friends do not exist as utility classes, so the constraint is enforced by the
tooling rather than by remembering it during review. Every colour on screen has
to mean something.

IBM Plex Sans for interface text, IBM Plex Mono with tabular figures for every
number, identifier, probability and timer — so live-updating values do not shift
horizontally as they change. Both are self-hosted, Latin subsets only, so the
application runs with no network access.

---

## Troubleshooting

**Dashboard shows Offline**
Check, in order: is uvicorn running; does `VITE_API_URL` match the host and port
it printed; does `AIDERS_CORS_ORIGINS` include `http://localhost:5173`. The
dashboard's error panel names which of these failed.

**`localhost` vs `127.0.0.1`**
Browsers treat these as different origins for CORS. Both are allowed by default.
If you change one, change the other to match.

**Vite says port 5173 is in use**
`strictPort` is on deliberately, so Vite fails instead of silently moving to
5174 — which would break the CORS allow-list and present as an unexplained
"Offline" badge. Free the port, or set a new one in both `vite.config.ts` and
`AIDERS_CORS_ORIGINS`.

**`uvicorn: command not found` / `not recognized`**
The virtualenv is not active. Re-run the activate command for your shell.

**PowerShell blocks the activate script**
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

**Windows: `python` opens the Microsoft Store**
Use `py -3` instead, as shown in the commands above.

**Type errors after pulling changes**
`npm install` — a dependency version probably moved.

---

## Phase roadmap

| Phase | Delivers | Status |
|---|---|---|
| 1 | Foundation, frozen contract | **complete** |
| 2 | Simulation core, tick clock, SSE | **complete** |
| 3 | Interactive disaster map | next |
| 4 | A\* routing, route cache |  |
| 5 | HMM + Bayesian Network, risk-driven rerouting |  |
| 6 | Knowledge engine, forward chaining, FOL |  |
| 7 | CSP resource allocation |  |
| 8 | Classical and hierarchical planning |  |
| 9 | Full pipeline integration, automatic replanning |  |
| 10 | Real-time event engine |  |
| 11 | UI polish |  |
| 12 | Analytics |  |
| 13 | Testing and hardening |  |
| 14 | Documentation and demo |  |
