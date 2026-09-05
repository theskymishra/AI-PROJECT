# Phase 10 Findings — HTN Plan Execution

## Objective

Convert the symbolic response plan produced by Phase 8 into explicit, observable state transitions in the in-memory simulation.

## Execution semantics

| HTN action | Emergency state | Ambulance state | Resource effect |
|---|---|---|---|
| DISPATCH_AMBULANCE | ALLOCATED → EN_ROUTE | DISPATCHED → EN_ROUTE | none |
| LOAD_PATIENTS | EN_ROUTE → ON_SCENE | EN_ROUTE → AT_SCENE | ambulance moves to emergency node |
| TRANSPORT_TO_HOSPITAL | ON_SCENE → TRANSPORTING | AT_SCENE → TRANSPORTING | ambulance moves to hospital node |
| HANDOFF_PATIENTS | TRANSPORTING → RESOLVED | TRANSPORTING → AVAILABLE | bed count is not decremented again |

## Why hospital beds are not decremented at handoff

Phase 7's `CSPAllocator.apply()` reserves the selected hospital capacity at allocation time. A second decrement during Phase 10 would double-count patients and make the dashboard incorrect. Phase 10 therefore preserves that accounting and only completes the operational workflow.

## Safety properties

- Execution is explicit rather than automatic.
- Only actions from the generated HTN plan are accepted.
- Ambulance/emergency/hospital IDs are validated before every transition.
- A changed resource assignment invalidates the stored plan.
- The execution cursor is in memory, consistent with the project's single-process simulation architecture.
- Resetting the execution session does not reset the simulation.

## Expected observable result

After a complete four-action plan for one emergency:

- emergency status becomes `RESOLVED`;
- ambulance status returns to `AVAILABLE`;
- ambulance assignment is cleared;
- active-emergency count decreases;
- the previously reserved hospital capacity remains correctly accounted for;
- the timeline records the executed HTN actions;
- the frontend receives a fresh snapshot through the `plan` SSE event.
