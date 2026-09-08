# AI-DERS Final Architecture — Phase 14

```text
React + TypeScript + Vite
        │
        ├── Dashboard / Map / AI modules
        ├── Execution / Monitoring
        ├── Explainability / Evaluation
        └── Final Report
                │
                ▼
        FastAPI REST + SSE
                │
                ▼
        In-memory WorldState
                │
        ┌───────┴─────────────────────────────────────────────┐
        │                                                     │
 Simulation + Sensors → HMM/BN → A* Routing → CSP Allocation │
        │                                      ↓              │
        │                                 HTN Planning         │
        │                                      ↓              │
        │                                HTN Execution         │
        │                                      ↓              │
        │                              Monitoring              │
        │                                      ↓              │
        │                              Explainability          │
        │                                      ↓              │
        │                              Evaluation              │
        │                                      ↓              │
        └────────────────────────── Final Report ─────────────┘
```

Phase 14 is an aggregation/reporting layer. It does not mutate the simulation and does not bypass the existing AI chain.
