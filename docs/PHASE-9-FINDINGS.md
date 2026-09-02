# Phase 9 Findings

## Technique

Dempster-Shafer Theory represents uncertain evidence with a basic probability assignment over subsets of the hypothesis frame.

For AI-DERS the frame is:

`{NORMAL, RISING, HIGH, CRITICAL}`

A reading such as `HIGH_WATER` supports `{HIGH, CRITICAL}` rather than claiming that the exact state is known. Remaining mass is placed on `THETA`, the full frame, to represent ignorance.

Independent sensor evidence is combined using Dempster's normalized rule. Conflict is retained as a metric rather than hidden.

## Output

The API exposes:

- combined mass assignments
- belief `Bel(H)`
- plausibility `Pl(H)`
- pignistic probability for decision-oriented display
- total evidence conflict
- source-level evidence and reliability

## Architectural boundary

Phase 9 is read-only. It consumes the same noisy sensor observations already produced by the simulation. It does not modify `WorldState`.
