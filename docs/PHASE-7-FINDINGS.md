# Phase 7 — CSP Resource Allocation

## Purpose

Phase 7 adds the **decision layer for emergency resources**. Phase 6 can reason
about the world and derive facts such as `Avoid(R17)`. Phase 7 uses those facts
along with live resource state to find a feasible ambulance + hospital assignment
for each active emergency.

## CSP model

- **Variables:** active emergencies.
- **Domain:** feasible `(ambulance, hospital)` pairs.
- **Constraints:**
  1. ambulance must be available;
  2. ambulance capacity must cover `emergency.patients`;
  3. hospital must have enough available beds;
  4. the ambulance must have a reachable route to the emergency;
  5. the emergency must have a reachable route to the hospital;
  6. one ambulance cannot serve two emergencies in the same allocation;
  7. hospital bed capacity cannot be oversubscribed.

## Algorithms

### MRV

Minimum Remaining Values selects the unassigned emergency with the smallest
current domain. This exposes the most constrained emergency first and reduces
unnecessary search.

### Backtracking

If a tentative assignment makes the remaining CSP impossible, the solver removes
that assignment and tries the next candidate.

### Forward checking

After an assignment, candidate values that can no longer be used are removed
from the remaining domains. The result reports the number of domain reductions.

### A* integration

The allocator does not invent a second routing algorithm. It asks the existing
Phase 4/5/6 `RoutingService` for reachability. Phase 6's `Avoid(R)` facts are
passed into that service, so roads inferred unsafe by symbolic reasoning are
softly avoided while blocked roads remain hard exclusions.

## Preview vs Apply

`POST /api/ai/allocate` accepts:

```json
{"apply": false}
```

for a read-only solve, or:

```json
{"apply": true}
```

for a solve followed by committing the assignments to the in-memory simulation.
The commit marks the emergency `ALLOCATED`, the ambulance `DISPATCHED`, stores
the assignment IDs, and decreases hospital available beds by the emergency's
transport patient count.

## Trace and metrics

The response exposes real algorithm metrics:

- `constraints_checked`
- `conflicts`
- `backtracks`
- `domain_reductions`
- `execution_ms`
- `trace`

The trace contains `ASSIGN`, `REJECT`, `PRUNE`, and `BACKTRACK` steps so the
algorithm can be demonstrated during a faculty review.

## Important boundary

This is still an academic simulation. The allocator is a decision-support
component and must not be presented as an operational emergency-management
system.
