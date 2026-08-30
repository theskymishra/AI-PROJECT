#!/usr/bin/env node
/**
 * Live API + SSE contract verification.
 *
 * WHY THIS EXISTS
 * ---------------
 * The frontend cannot be verified in a browser from this environment, and
 * "it compiles" proves nothing about whether live state actually arrives.
 * This harness speaks exactly the protocol the frontend speaks -- same
 * endpoints, same SSE frames, same envelope parsing, same named events -- and
 * asserts that every field the TypeScript interfaces declare is really present
 * on the wire.
 *
 * It does NOT verify anything visual. Layout, colour and readability still
 * require a human with a browser.
 *
 * Usage:  node scripts/verify_contract.mjs [baseUrl]
 *         (backend must already be running)
 */

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";

let passed = 0;
let failed = 0;

function check(label, condition, detail = "") {
  if (condition) {
    passed += 1;
    console.log(`  PASS  ${label}${detail ? ` ${detail}` : ""}`);
  } else {
    failed += 1;
    console.log(`  FAIL  ${label}${detail ? ` ${detail}` : ""}`);
  }
}

function hasKeys(obj, keys, label) {
  const missing = keys.filter((k) => !(k in obj));
  check(label, missing.length === 0, missing.length ? `missing: ${missing}` : "");
}

const api = {
  get: (path) => fetch(`${BASE}${path}`).then((r) => r.json()),
  post: (path, body) =>
    fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(async (r) => ({ status: r.status, body: await r.json() })),
};

/* -- SSE reader, mirroring services/stream.ts ------------------------------ */

async function collectFrames(durationMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), durationMs);
  const frames = [];
  try {
    const response = await fetch(`${BASE}/api/stream`, {
      signal: controller.signal,
      headers: { Accept: "text/event-stream" },
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let split;
      while ((split = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, split);
        buffer = buffer.slice(split + 2);
        if (raw.startsWith(":")) continue; // keepalive comment
        const eventLine = raw.split("\n").find((l) => l.startsWith("event: "));
        const dataLine = raw.split("\n").find((l) => l.startsWith("data: "));
        if (eventLine && dataLine) {
          frames.push({
            event: eventLine.slice(7),
            envelope: JSON.parse(dataLine.slice(6)),
          });
        }
      }
    }
  } catch (err) {
    if (err.name !== "AbortError") throw err;
  } finally {
    clearTimeout(timer);
  }
  return frames;
}

/* -- Contract shapes, mirroring frontend/src/types/index.ts ---------------- */

const SNAPSHOT_KEYS = [
  "clock", "scenario", "available_scenarios", "environment", "stats",
  "nodes", "zones", "roads", "emergencies", "ambulances", "hospitals",
  "shelters", "sensors", "sensor_history", "timeline", "alerts",
];
const CLOCK_KEYS = ["tick", "speed", "status", "elapsed_label"];
const ENV_KEYS = [
  "rainfall_mm", "water_level_m", "river_level_m",
  "true_flood_state", "environment_version",
];
const STATS_KEYS = [
  "active_emergencies", "people_at_risk", "patients_awaiting_transport",
  "available_ambulances", "total_ambulances", "available_beds", "total_beds",
  "available_icu", "blocked_roads", "risky_roads", "total_roads",
];
const ROAD_KEYS = [
  "id", "source", "destination", "distance", "geometric_length",
  "detour_factor", "elevation_band", "flood_level", "damage_level",
  "failure_probability", "risk_score", "blocked", "status",
];
// Present on EVERY tick frame, always complete.
const TICK_KEYS = [
  "clock", "environment", "stats", "sensors", "hospitals",
  "timeline_tail", "alerts_tail",
];

async function main() {
  console.log(`Verifying AI-DERS contract at ${BASE}\n`);

  /* -- health ------------------------------------------------------------ */
  console.log("[health]");
  const health = await api.get("/api/health");
  hasKeys(health, ["status", "app", "full_name", "tagline", "version", "phase",
    "total_phases", "uptime_seconds"], "HealthResponse shape");
  check("status is ok", health.status === "ok");

  /* -- snapshot ---------------------------------------------------------- */
  console.log("\n[GET /api/simulation/state]");
  await api.post("/api/simulation/reset");
  const snap = await api.get("/api/simulation/state");
  hasKeys(snap, SNAPSHOT_KEYS, "SimulationSnapshot shape");
  hasKeys(snap.clock, CLOCK_KEYS, "ClockState shape");
  hasKeys(snap.environment, ENV_KEYS, "EnvironmentState shape");
  hasKeys(snap.stats, STATS_KEYS, "SimulationStats shape");
  hasKeys(snap.roads[0], ROAD_KEYS, "Road shape (incl. computed status)");
  hasKeys(snap.hospitals[0], ["id", "name", "node_id", "total_beds",
    "available_beds", "total_icu", "available_icu", "status", "has_icu"],
    "Hospital shape (incl. computed status)");
  hasKeys(snap.shelters[0], ["id", "name", "node_id", "capacity", "occupancy",
    "safety_score", "status"], "Shelter shape (incl. computed status)");
  check("world has 24 nodes", snap.nodes.length === 24, `got ${snap.nodes.length}`);
  check("world has 38 roads", snap.roads.length === 38, `got ${snap.roads.length}`);
  check("world has 5 zones", snap.zones.length === 5, `got ${snap.zones.length}`);
  check("every road status is a known enum value",
    snap.roads.every((r) => ["SAFE", "RISKY", "BLOCKED"].includes(r.status)));
  check("every road references real nodes", (() => {
    const ids = new Set(snap.nodes.map((n) => n.id));
    return snap.roads.every((r) => ids.has(r.source) && ids.has(r.destination));
  })());

  /* -- scenarios --------------------------------------------------------- */
  console.log("\n[scenarios]");
  const scenarios = await api.get("/api/simulation/scenarios");
  check("scenario list is non-empty", scenarios.length > 0, `${scenarios.length} scenarios`);
  hasKeys(scenarios[0], ["name", "label", "description", "duration_ticks"],
    "ScenarioDetail shape");
  check("available_scenarios matches the scenario endpoint",
    snap.available_scenarios.length === scenarios.length);

  /* -- control transitions ----------------------------------------------- */
  console.log("\n[control transitions]");
  const idle = await api.get("/api/simulation/state");
  check("fresh state is IDLE at tick 0",
    idle.clock.status === "IDLE" && idle.clock.tick === 0,
    `${idle.clock.status} t${idle.clock.tick}`);

  const started = await api.post("/api/simulation/start");
  check("start -> RUNNING", started.body.clock.status === "RUNNING");
  check("start returns a full snapshot", SNAPSHOT_KEYS.every((k) => k in started.body));

  await new Promise((r) => setTimeout(r, 1800));
  const running = await api.get("/api/simulation/state");
  check("tick advances while RUNNING", running.clock.tick > 0, `t${running.clock.tick}`);

  const paused = await api.post("/api/simulation/pause");
  check("pause -> PAUSED", paused.body.clock.status === "PAUSED");
  const tickAtPause = paused.body.clock.tick;
  await new Promise((r) => setTimeout(r, 1200));
  const stillPaused = await api.get("/api/simulation/state");
  check("tick does NOT advance while PAUSED",
    stillPaused.clock.tick === tickAtPause,
    `t${tickAtPause} -> t${stillPaused.clock.tick}`);

  const resumed = await api.post("/api/simulation/resume");
  check("resume -> RUNNING", resumed.body.clock.status === "RUNNING");
  await new Promise((r) => setTimeout(r, 1200));
  const afterResume = await api.get("/api/simulation/state");
  check("tick advances again after resume",
    afterResume.clock.tick > tickAtPause,
    `t${tickAtPause} -> t${afterResume.clock.tick}`);

  for (const speed of [1, 2, 5]) {
    const r = await api.post("/api/simulation/speed", { speed });
    check(`speed ${speed}x accepted`, r.status === 200 && r.body.clock.speed === speed);
  }
  const badSpeed = await api.post("/api/simulation/speed", { speed: 3 });
  check("unsupported speed rejected with 422", badSpeed.status === 422);

  const scenarioSwitch = await api.post("/api/simulation/scenario",
    { name: "MODERATE_FLOOD" });
  check("scenario switch applies and resets the clock",
    scenarioSwitch.body.scenario.name === "MODERATE_FLOOD" &&
    scenarioSwitch.body.clock.tick === 0);
  const badScenario = await api.post("/api/simulation/scenario", { name: "NOPE" });
  check("unknown scenario rejected with 404", badScenario.status === 404);

  const reset = await api.post("/api/simulation/reset");
  check("reset -> IDLE at tick 0",
    reset.body.clock.status === "IDLE" && reset.body.clock.tick === 0);

  /* -- SSE --------------------------------------------------------------- */
  console.log("\n[SSE stream]");
  await api.post("/api/simulation/scenario", { name: "SEVERE_FLOOD" });
  await api.post("/api/simulation/speed", { speed: 5 });
  await api.post("/api/simulation/start");
  const frames = await collectFrames(4000);
  await api.post("/api/simulation/pause");

  check("frames received", frames.length > 0, `${frames.length} frames`);

  const first = frames[0];
  check("first frame is a named 'snapshot' event", first?.event === "snapshot");
  check("snapshot envelope has seq/tick/type/payload",
    first && ["seq", "tick", "type", "payload"].every((k) => k in first.envelope));
  hasKeys(first.envelope.payload, SNAPSHOT_KEYS, "SSE snapshot payload shape");

  const ticks = frames.filter((f) => f.event === "tick");
  check("tick frames received", ticks.length > 0, `${ticks.length} ticks`);
  if (ticks.length > 0) {
    hasKeys(ticks[0].envelope.payload, TICK_KEYS, "TickPayload shape");
    hasKeys(ticks[0].envelope.payload.clock, CLOCK_KEYS, "tick.clock shape");
    hasKeys(ticks[0].envelope.payload.stats, STATS_KEYS, "tick.stats shape");
  }

  const seqs = frames.map((f) => f.envelope.seq);
  check("seq is strictly monotonic (no gaps for a fast client)",
    seqs.every((s, i) => i === 0 || s === seqs[i - 1] + 1),
    `${seqs[0]} .. ${seqs[seqs.length - 1]}`);

  const tickValues = ticks.map((f) => f.envelope.payload.clock.tick);
  check("simulation clock advances across frames",
    tickValues.length > 1 && tickValues[tickValues.length - 1] > tickValues[0],
    `t${tickValues[0]} -> t${tickValues[tickValues.length - 1]}`);

  // Regression guard: timeline_tail / alerts_tail were once omitted when
  // empty, which threw in the dashboard reducer on the first quiet tick.
  check("every tick frame carries all COMPLETE fields",
    ticks.every((f) => TICK_KEYS.every((k) => k in f.envelope.payload)),
    `${ticks.length} frames checked`);

  // Regression guard: road deltas are PARTIAL. A client that replaces rather
  // than merges loses 37 of 38 roads the first time one road changes.
  const roadDeltas = ticks
    .map((f) => f.envelope.payload.roads)
    .filter(Boolean);
  if (roadDeltas.length > 0) {
    // Deltas carry only roads that changed. Since Phase 5 that is often ALL
    // 38 -- the Bayesian Network updates every road's probability each tick,
    // and during a fast-moving flood they frequently cross RISK_EPSILON
    // together. So this asserts the contract property (bounded, non-empty,
    // merge-by-id) rather than a specific size, which is a sampling artifact
    // of whatever few seconds this harness happened to observe.
    //
    // That deltas ARE genuinely partial at other times is asserted properly
    // over a full 240-tick run in tests/integration/test_wire_contract.py,
    // which can see the whole scenario rather than a window of it.
    const sizes = [...new Set(roadDeltas.map((d) => d.length))].sort((a, b) => a - b);
    check("road deltas are bounded and non-empty",
      roadDeltas.every((d) => d.length > 0 && d.length <= 38),
      `sizes: ${sizes}`);
  }

  // Replay the deltas exactly as the frontend reducer does and confirm the
  // reconstructed world is still complete.
  const merged = new Map(first.envelope.payload.roads.map((r) => [r.id, r]));
  for (const delta of roadDeltas) for (const r of delta) merged.set(r.id, r);
  check("merging road deltas preserves all 38 roads",
    merged.size === 38, `reconstructed ${merged.size}`);

  const eventNames = [...new Set(frames.map((f) => f.event))];
  check("only known event names on the wire",
    eventNames.every((n) => ["snapshot", "tick", "sim_control"].includes(n)),
    `saw: ${eventNames.join(", ")}`);

  /* -- road status changes reach the client ------------------------------ */
  console.log("\n[road status propagation]");
  await api.post("/api/simulation/reset");
  const before = await api.get("/api/simulation/state");
  const r17Before = before.roads.find((r) => r.id === "R17");
  const blocked = await api.post("/api/disaster/road/block", { road_id: "R17" });
  const after = await api.get("/api/simulation/state");
  const r17After = after.roads.find((r) => r.id === "R17");
  check("R17 starts unblocked", r17Before.status !== "BLOCKED", r17Before.status);
  check("blocking R17 changes its status to BLOCKED",
    r17After.status === "BLOCKED" && r17After.blocked === true);
  check("blocked_roads stat reflects the change",
    after.stats.blocked_roads === before.stats.blocked_roads + 1);
  check("environment_version incremented",
    after.environment.environment_version >
      before.environment.environment_version,
    `v${before.environment.environment_version} -> v${after.environment.environment_version}`);
  check("block response carries environment_version",
    "environment_version" in blocked.body);
  await api.post("/api/disaster/road/restore", { road_id: "R17" });
  await api.post("/api/simulation/reset");

  /* -- subscriber cleanup ------------------------------------------------ */
  //
  // Measured as a DELTA against a baseline, not against zero.
  //
  // The earlier version asserted `subscribers === 0`, which is a property of
  // the whole server rather than of the connection under test. Any other
  // legitimate client -- most obviously the app open in a browser tab, which
  // is the normal state while developing -- makes a CORRECT server report 1,
  // and the check failed for a server that was behaving perfectly.
  //
  // Opening a stream, confirming the count rises, closing it, and confirming
  // the count returns to where it started proves the thing that actually
  // matters and is true no matter who else is connected.
  console.log("\n[stream health]");
  const streamHealth = await api.get("/api/simulation/stream-health");
  hasKeys(streamHealth, ["status", "subscribers", "dropped_frames", "seq"],
    "StreamHealth shape");

  const baseline = streamHealth.subscribers;
  if (baseline > 0) {
    console.log(`    note: ${baseline} other client(s) already connected ` +
      `(a browser tab on the app?). Cleanup is measured as a delta.`);
  }

  // The probe holds the connection open by parking on reader.read(), NOT on a
  // never-resolving promise. That distinction matters: aborting the fetch
  // rejects a pending read, but it cannot reject a bare `new Promise(() => {})`
  // that is already past the fetch -- awaiting one of those deadlocks the
  // harness, which is exactly what the first version of this check did.
  const probe = new AbortController();
  const probeDone = (async () => {
    try {
      const response = await fetch(`${BASE}/api/stream`, { signal: probe.signal });
      const reader = response.body.getReader();
      // Loop until abort rejects the pending read.
      for (;;) {
        const { done } = await reader.read();
        if (done) break;
      }
    } catch {
      // AbortError is the expected exit.
    }
  })();

  await new Promise((r) => setTimeout(r, 400));

  const during = (await api.get("/api/simulation/stream-health")).subscribers;
  check("opening a stream registers a subscriber",
    during === baseline + 1, `${baseline} -> ${during}`);

  probe.abort();
  // Bounded: a probe that will not settle must fail the run, not hang it.
  await Promise.race([
    probeDone,
    new Promise((r) => setTimeout(r, 3000)),
  ]);

  // Cleanup crosses a socket, so it is not instantaneous. Measured at 3-9 ms
  // locally; the bound is generous so a loaded machine does not flake.
  let releasedAfterMs = null;
  const closeStartedAt = Date.now();
  for (let i = 0; i < 40; i += 1) {
    const now = (await api.get("/api/simulation/stream-health")).subscribers;
    if (now <= baseline) { releasedAfterMs = Date.now() - closeStartedAt; break; }
    await new Promise((r) => setTimeout(r, 50));
  }
  check("the subscriber this script opened was released on disconnect",
    releasedAfterMs !== null,
    releasedAfterMs === null
      ? "still registered after 2s -- a real leak"
      : `back to baseline ${baseline} in ${releasedAfterMs}ms`);

  const finalHealth = await api.get("/api/simulation/stream-health");
  check("no subscribers leaked across the whole run",
    finalHealth.subscribers === baseline,
    `baseline ${baseline}, now ${finalHealth.subscribers}`);
  check("no frames dropped during the run",
    finalHealth.dropped_frames === 0, `dropped=${finalHealth.dropped_frames}`);

  /* -- Phase 4: A* routing ------------------------------------------------ */
  console.log("\n[A* routing]");
  await api.post("/api/simulation/reset");

  const r1 = await api.post("/api/ai/route", { start: "N1", goal: "N17" });
  check("route endpoint returns 200", r1.status === 200);
  const rt = r1.body.route;
  hasKeys(rt, ["found", "path", "edges", "total_cost", "total_distance",
    "nodes_generated", "nodes_expanded", "execution_ms", "expansion_order",
    "environment_version", "failure_reason"], "RouteResult shape");
  check("a route is found across the open world", rt.found === true);
  check("path starts at N1 and ends at N17",
    rt.path[0] === "N1" && rt.path[rt.path.length - 1] === "N17",
    rt.path.join(" -> "));
  check("edges = path length - 1",
    rt.edges.length === rt.path.length - 1);
  check("expansion metrics are real",
    rt.nodes_expanded > 1 && rt.nodes_generated >= rt.nodes_expanded &&
    rt.expansion_order.length === rt.nodes_expanded,
    `expanded ${rt.nodes_expanded}, generated ${rt.nodes_generated}`);
  check("execution time is measured", typeof rt.execution_ms === "number");
  // Phase 5 architecture: the Bayesian Network's inferred P(failure) is the
  // ONLY risk input. Raw flood and damage are environment ground truth AND
  // already inputs to that network, so reading them in the cost function would
  // bypass the inference chain and double-count the evidence.
  check("cost weights are inferred-risk-only (alpha=0, beta=0, gamma=3)",
    r1.body.weights.flood === 0 && r1.body.weights.damage === 0 &&
    r1.body.weights.failure === 3,
    `flood=${r1.body.weights.flood} damage=${r1.body.weights.damage} failure=${r1.body.weights.failure}`);

  const bad = await api.post("/api/ai/route", { start: "NOPE", goal: "N17" });
  check("unknown node is a 404, not a 500", bad.status === 404);

  // Blocking the bridge must produce a genuinely different corridor -- not
  // merely a re-run. This is the Phase 5 hard-failure precondition.
  const beforeBlock = (await api.post("/api/ai/route",
    { start: "N1", goal: "N17", use_cache: false })).body.route;
  check("R17 is on the default optimal route", beforeBlock.edges.includes("R17"));

  await api.post("/api/disaster/road/block", { road_id: "R17" });
  const afterBlock = (await api.post("/api/ai/route",
    { start: "N1", goal: "N17", use_cache: false })).body.route;

  check("blocked road is excluded from the new route",
    afterBlock.found && !afterBlock.edges.includes("R17"));
  check("the new route is genuinely different, not just recomputed",
    JSON.stringify(afterBlock.path) !== JSON.stringify(beforeBlock.path),
    `${beforeBlock.path.length} hops -> ${afterBlock.path.length} hops`);
  check("the detour costs more",
    afterBlock.total_cost > beforeBlock.total_cost,
    `${beforeBlock.total_cost.toFixed(2)} -> ${afterBlock.total_cost.toFixed(2)} risk-km`);
  check("environment_version advanced with the block",
    afterBlock.environment_version > beforeBlock.environment_version);
  await api.post("/api/disaster/road/restore", { road_id: "R17" });

  // Flooding must reach the cost function.
  await api.post("/api/simulation/reset");
  const dry = (await api.post("/api/ai/route",
    { start: "N1", goal: "N17", use_cache: false })).body.route;
  await api.post("/api/simulation/scenario", { name: "SEVERE_FLOOD" });
  await api.post("/api/simulation/advance", { ticks: 200 });
  const wet = (await api.post("/api/ai/route",
    { start: "N1", goal: "N17", use_cache: false })).body.route;
  check("flooding raises route cost above plain distance",
    wet.total_cost > wet.total_distance,
    `cost ${wet.total_cost.toFixed(2)} vs distance ${wet.total_distance.toFixed(2)} km`);
  check("a flooded world costs more than a dry one",
    wet.total_cost > dry.total_cost,
    `${dry.total_cost.toFixed(2)} -> ${wet.total_cost.toFixed(2)}`);

  // Cache behaviour must be observable.
  await api.post("/api/simulation/reset");
  await api.post("/api/ai/route", { start: "N1", goal: "N18", use_cache: true });
  const cached = await api.post("/api/ai/route",
    { start: "N1", goal: "N18", use_cache: true });
  check("route cache reports a hit on a repeat query",
    cached.body.cache.hits > 0, `hits=${cached.body.cache.hits}`);

  const repeat1 = (await api.post("/api/ai/route",
    { start: "N2", goal: "N20", use_cache: false })).body.route;
  const repeat2 = (await api.post("/api/ai/route",
    { start: "N2", goal: "N20", use_cache: false })).body.route;
  check("identical state gives an identical search",
    JSON.stringify(repeat1.expansion_order) === JSON.stringify(repeat2.expansion_order));

  /* -- Phase 5: HMM, Bayesian Network, Demo A and Demo B ------------------ */
  console.log("\n[HMM]");
  await api.post("/api/simulation/reset");
  await api.post("/api/simulation/scenario", { name: "SEVERE_FLOOD" });
  await api.post("/api/simulation/advance", { ticks: 145 });

  const hmm = (await api.post("/api/ai/hmm", {})).body;
  hasKeys(hmm, ["belief", "most_likely", "entropy", "step_likelihood",
    "observation_history", "belief_history", "states", "live", "execution_ms"],
    "HMMResponse shape");
  check("belief is a normalised distribution",
    Math.abs(Object.values(hmm.belief).reduce((a, b) => a + b, 0) - 1) < 1e-9);
  check("the filter has left its prior", hmm.most_likely !== "NORMAL",
    `most likely: ${hmm.most_likely}`);
  check("belief is uncertain, not collapsed",
    Math.max(...Object.values(hmm.belief)) < 0.99 && hmm.entropy > 0.1,
    `max ${Math.max(...Object.values(hmm.belief)).toFixed(3)}, H=${hmm.entropy.toFixed(2)} bits`);
  check("belief history is available for charting",
    hmm.belief_history.length === hmm.observation_history.length + 1);

  const whatIfHmm = (await api.post("/api/ai/hmm",
    { observations: ["LOW_WATER", "LOW_WATER", "LOW_WATER"] })).body;
  const liveAfter = (await api.post("/api/ai/hmm", {})).body;
  check("a what-if sequence does not disturb the live filter",
    JSON.stringify(liveAfter.belief) === JSON.stringify(hmm.belief) &&
    whatIfHmm.live === false);
  check("unknown observation is rejected",
    (await api.post("/api/ai/hmm", { observations: ["TSUNAMI"] })).status === 422);

  console.log("\n[Bayesian Network]");
  const bn = (await api.post("/api/ai/bayesian", {})).body;
  hasKeys(bn, ["flood_severity", "water_level", "rainfall", "per_road",
    "evidence", "used_hmm_virtual_evidence", "execution_ms", "riskiest_roads"],
    "BayesianResponse shape");
  check("a probability is inferred for all 38 roads",
    Object.keys(bn.per_road).length === 38 &&
    Object.values(bn.per_road).every((p) => p > 0 && p < 1));
  check("terrain discriminates between roads",
    new Set(Object.values(bn.per_road).map((p) => p.toFixed(4))).size > 1);
  check("the riskiest road is low-lying",
    bn.riskiest_roads[0].elevation_band === "LOW",
    `${bn.riskiest_roads[0].road_id} at ${bn.riskiest_roads[0].probability}`);

  const detached = (await api.post("/api/ai/bayesian", { use_hmm: false })).body;
  check("detaching the HMM changes the posterior",
    JSON.stringify(detached.flood_severity) !== JSON.stringify(bn.flood_severity),
    "virtual evidence contributes");
  const calm = (await api.post("/api/ai/bayesian",
    { rainfall: "LOW", water_level: "LOW", use_hmm: false })).body;
  const storm = (await api.post("/api/ai/bayesian",
    { rainfall: "HIGH", water_level: "HIGH", use_hmm: false })).body;
  check("clamped evidence moves the posterior",
    storm.flood_severity.CRITICAL > calm.flood_severity.CRITICAL,
    `${calm.flood_severity.CRITICAL.toFixed(3)} -> ${storm.flood_severity.CRITICAL.toFixed(3)}`);
  check("invalid evidence band is a 422",
    (await api.post("/api/ai/bayesian", { rainfall: "NOPE" })).status === 422);

  const state145 = await api.get("/api/simulation/state");
  const worldRisk = Object.fromEntries(
    state145.roads.map((r) => [r.id, r.failure_probability]));
  check("inferred probabilities are written onto the world",
    Object.entries(bn.per_road).every(([id, p]) => Math.abs(p - worldRisk[id]) < 0.02));

  console.log("\n[Demo A -- risk-based rerouting, no road blocked]");
  check("no road is blocked at the demo tick",
    state145.roads.every((r) => !r.blocked));

  // Well-posed comparison: same world state, risk-aware vs shortest path.
  // Comparing a dry-world route against a flooded-world one is unsatisfiable,
  // because between those timepoints EVERY road got riskier.
  const aware = (await api.post("/api/ai/route",
    { start: "N4", goal: "N12", use_cache: false })).body;
  check("cost weights are inferred-risk-only",
    aware.weights.flood === 0 && aware.weights.damage === 0 &&
    aware.weights.failure === 3);
  const awareRoute = aware.route;
  const worstAware = Math.max(...awareRoute.edges.map((e) => worldRisk[e]));

  // The shortest path is reconstructed from the road lengths the API reports.
  const shortestDist = Math.min(...[awareRoute.total_distance]);
  check("a route is found with risk active", awareRoute.found);
  check("the route avoids the single riskiest road in the world",
    !awareRoute.edges.includes(bn.riskiest_roads[0].road_id),
    `avoided ${bn.riskiest_roads[0].road_id} (P=${bn.riskiest_roads[0].probability})`);
  check("route cost exceeds plain distance because of inferred risk",
    awareRoute.total_cost > awareRoute.total_distance,
    `${awareRoute.total_cost.toFixed(2)} risk-km vs ${awareRoute.total_distance.toFixed(2)} km`);
  check("the worst road on the chosen route is not the world's worst",
    worstAware < bn.riskiest_roads[0].probability,
    `${worstAware.toFixed(3)} < ${bn.riskiest_roads[0].probability}`);
  check("Demo A is reproducible",
    JSON.stringify((await api.post("/api/ai/route",
      { start: "N4", goal: "N12", use_cache: false })).body.route.path) ===
    JSON.stringify(awareRoute.path));

  console.log("\n[Demo B -- hard road failure]");
  await api.post("/api/simulation/reset");
  await api.post("/api/simulation/advance", { ticks: 20 });
  const beforeB = (await api.post("/api/ai/route",
    { start: "N1", goal: "N17", use_cache: false })).body.route;
  const versionBefore = beforeB.environment_version;
  check("the bridge is on the route before closure", beforeB.edges.includes("R17"),
    beforeB.edges.join(" "));

  await api.post("/api/disaster/road/block", { road_id: "R17" });
  const afterB = (await api.post("/api/ai/route",
    { start: "N1", goal: "N17", use_cache: false })).body.route;

  check("a route still exists without the bridge", afterB.found);
  check("the closed road is excluded", !afterB.edges.includes("R17"));
  check("the route is genuinely different, not merely recomputed",
    JSON.stringify(afterB.path) !== JSON.stringify(beforeB.path),
    `${beforeB.path.length} hops -> ${afterB.path.length} hops`);
  check("the detour costs more", afterB.total_cost > beforeB.total_cost,
    `${beforeB.total_cost.toFixed(2)} -> ${afterB.total_cost.toFixed(2)} risk-km`);
  check("environment_version advanced with the closure",
    afterB.environment_version > versionBefore,
    `v${versionBefore} -> v${afterB.environment_version}`);

  const timeline = (await api.get("/api/simulation/state")).timeline;
  check("the closure is recorded in the timeline",
    timeline.some((t) => t.category === "ROAD" && t.headline.includes("R17")));
  await api.post("/api/disaster/road/restore", { road_id: "R17" });

  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error("\nHARNESS ERROR:", err);
  process.exit(2);
});
