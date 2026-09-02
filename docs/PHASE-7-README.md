# Phase 7 Demo Flow

1. Start the backend and frontend.
2. Choose a disaster scenario and let the simulation create active emergencies.
3. Open **Resources**.
4. Click **Preview allocation**.
5. Explain the result:
   - emergency = CSP variable;
   - ambulance/hospital pairs = domain values;
   - capacity/availability/reachability = constraints;
   - MRV chooses the next emergency;
   - forward checking prunes impossible choices;
   - backtracking tries alternatives when a conflict occurs.
6. Open **AI Reasoning** to show the Phase 6 `Avoid(R)` facts that influence
   Phase 7's route-feasibility checks.
7. Click **Apply allocation** to commit the selected assignments.

The best faculty demonstration is to first preview, show the trace and metrics,
then apply the allocation and show the changed emergency/ambulance/hospital
state.
