# PHASE 5 — FINDINGS AND TWO BLOCKING DECISIONS

**Status: PARTIAL.** The HMM and Bayesian Network are built, unit-tested and
verified in isolation. They are **not wired into the tick loop**, because
switching them on causes two measured problems that change approved
architecture. Both need a decision.

Suite is green at 398 backend / 81 frontend. Nothing is broken. Nothing is
faked.

---

## What is done and verified

| Component | Status |
|---|---|
| `ai/probability/hmm.py` — forward algorithm, filtering | built, 24 tests |
| `ai/probability/bayesian.py` — two-pathway BN, virtual evidence, noisy-OR | built, 33 tests |
| `services/risk_service.py` — sensors → HMM → BN → `road.failure_probability` | built, **not wired** |
| HMM/BN parameters in `config.py` | all 29 distributions normalise |
| Noisy-OR anchors | 0.039 / 0.695 / 0.967 — match Phase 0 exactly |

The HMM demonstrably works. Filtering a rising-water sequence:

```
prior            NORMAL 0.90  RISING 0.08  HIGH 0.02  CRITICAL 0.00
MEDIUM_WATER     NORMAL 0.61  RISING 0.35  HIGH 0.05  CRITICAL 0.00   H=1.18
HIGH_WATER       NORMAL 0.15  RISING 0.45  HIGH 0.36  CRITICAL 0.04   H=1.65
HIGH_WATER       NORMAL 0.03  RISING 0.27  HIGH 0.58  CRITICAL 0.13   H=1.48
RAPIDLY_RISING   NORMAL 0.00  RISING 0.13  HIGH 0.43  CRITICAL 0.43   H=1.45
RAPIDLY_RISING   NORMAL 0.00  RISING 0.06  HIGH 0.28  CRITICAL 0.66   H=1.15
```

Entropy stays above 1 bit throughout — the posterior never collapses, which is
the property that keeps the panel from looking hard-coded. Against live
simulation state the belief visibly **lags** the truth (tick 120: truth
RISING, belief HIGH; tick 150: truth HIGH, belief RISING). That lag is the
interesting behaviour and it is real.

---

## DECISION 1 — Demo A cannot be satisfied by the approved cost model

**Measured:** with the Phase 4 cost function

```
w(e) = distance × (1 + 2·flood_level + 1.5·damage + 3·P_fail)
```

setting **γ = 0 changes no route at all**. Across all 552 node pairs, the
risk-aware and risk-blind routes are identical. The Bayesian Network's output
currently has **zero effect on routing**.

**Cause:** `flood_level` and `P_fail` are collinear. Both are driven by the
same terrain elevation band, so adding `γ·P_fail` scales every route's cost
roughly proportionally and never changes their ranking. The 22 pairs that do
reroute as water rises are driven entirely by the raw `α·flood_level` term,
which has been live since Phase 4.

**This means the Phase 0 claim that the BN feeds A\* and changes the route is,
as built, false.** The route is decided by raw flood level alone.

### The principled fix, and why I stopped short of applying it

Retire the raw `α·flood_level` term. Rationale, in order of strength:

1. `road.flood_level` is **environment ground truth**. The architecture is
   "agent perceives noisy sensors, infers hidden state." Letting A\* read
   flood level directly bypasses the entire inference chain — the agent is
   reading the answer instead of inferring it. Same objection already
   documented for the water gauge.
2. The BN exists precisely to convert raw observations into a calibrated
   failure probability. Feeding raw flood in parallel double-counts it.
3. Phase 0's pipeline diagram shows risk flowing sensors → HMM → BN → cost.
   It does **not** show `flood_level` flowing directly to cost. The `α` term
   was a Phase 4 stopgap, documented at the time as necessary *because* P_fail
   was zero.

**Measured with `α = 0`:**

| config | pairs longer **and** strictly safer |
|---|---|
| α=0, β=0, γ=3 | 4 |
| α=0, β=1.5, γ=3 | **22** |

Best example (α=0, β=1.5): **N17 → N3**, Highland Hospital to Riverside Clinic.

```
shortest path   44.66 km   worst road P(fail) 0.790
risk-aware      50.42 km   worst road P(fail) 0.537
```

The agent accepts **+5.76 km (13% longer)** to cut the worst road's failure
probability by **a third**. No road blocked. That is Demo A, properly
demonstrated.

**Why I did not just apply it:** the gap between 4 and 22 pairs is decided
entirely by `β`, and I cannot justify 1.5 over 0 from first principles —
`damage_level` is an input to the BN too, so keeping `β` reintroduces the same
double-counting the change is meant to remove. Choosing β=1.5 because it
produces a better demo is tuning parameters until a demo works, which is what
I said at the end of Phase 4 I would flag rather than do.

**Decision needed:**

- **(a)** α=0, β=0, γ=3 — architecturally clean, one risk input, all of it
  inferred. 4 demonstrable pairs.
- **(b)** α=0, β=1.5, γ=3 — 22 demonstrable pairs, but damage is
  double-counted.
- **(c)** Keep Phase 4 weights, accept the BN does not change routes, and
  describe it honestly as producing a risk estimate the router does not yet
  act on.

I would choose **(a)** and pick the demo pair from its 4, because "our
Bayesian Network output is the only risk input to the router" survives a viva
and "we tuned a weight until the demo worked" does not.

### Phase 0's "safer" criterion is also ill-posed

The approved acceptance says *"every road on `route_after` has lower `P_fail`
than the worst road on `route_before`."* But `route_before` is measured in a
dry world and `route_after` in a flooded one — **every** road is riskier, so
the criterion is unsatisfiable regardless of implementation.

The well-posed version compares **risk-aware against risk-blind at the same
timepoint**: at a flooded tick, the chosen route must be longer and strictly
safer than the shortest path. That is what the table above measures, and it is
a stronger claim.

---

## DECISION 2 — the BN defeats the route cache

**Measured:** with `risk_service.assess()` wired into `step()`,
`environment_version` reaches **211 bumps in 300 ticks** — against my own
Phase 2 assertion of `< 60`. That test failed, correctly, and is why the
wiring is currently reverted.

**Cause:** the HMM belief legitimately swings on noisy observations, `P_fail`
follows it, and some road crosses `RISK_EPSILON = 0.05` on roughly 70% of
ticks. The route cache would essentially never serve a cross-tick hit — the
exact failure mode Phase 0 §2.1 introduced the epsilon to prevent.

**The uncomfortable part:** each bump is *arguably correct*. The agent's risk
estimate really did change. It is not floating-point noise.

**Options:**

- **(a)** Accept it. Reframe the cache as **intra-tick only** — which is what
  Phase 7's CSP actually needs (one route table per allocation pass, breaking
  the CSP↔A\* cycle). Cross-tick caching during an evolving disaster is not
  meaningful. Update the Phase 2 test to assert the intra-tick property
  instead.
- **(b)** Raise `RISK_EPSILON` until the bump rate is acceptable. This is
  tuning to hide a symptom.
- **(c)** Bump only when the routing-relevant *ranking* could change, not when
  any probability moves. Correct in principle, materially more complex.

I would choose **(a)**. It requires changing a test I wrote, which I will not
do without you agreeing, because that test encodes a Phase 0 design decision.

---

## What remains for Phase 5 once decided

- Wire `risk_service` into `step()` (one line, already written and commented
  in place at `engine.py`)
- `POST /api/ai/hmm` and `POST /api/ai/bayesian`
- Risk Analysis page: HMM belief chart, BN structure, sensor charts,
  what-if mode with the HMM detached
- Demo A and Demo B integration tests
- Extend `verify_contract.mjs` with both demos

None of that is blocked on anything except these two decisions. All of it is
mechanical once the cost model is settled.

---

## Honest summary

Phase 5's algorithms work. What does not work is the claim that they change
routing — and the reason is a cost-model design flaw inherited from Phase 4,
not a defect in the HMM or the Bayesian Network. Discovering it now, with
measurements, is better than discovering it in a viva when someone asks what
the Bayesian Network actually does.
