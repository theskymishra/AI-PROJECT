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
    check("road deltas are partial (client must merge by id)",
      Math.min(...roadDeltas.map((d) => d.length)) < 38,
      `sizes: ${[...new Set(roadDeltas.map((d) => d.length))].sort((a, b) => a - b)}`);
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
  console.log("\n[stream health]");
  const streamHealth = await api.get("/api/simulation/stream-health");
  hasKeys(streamHealth, ["status", "subscribers", "dropped_frames", "seq"],
    "StreamHealth shape");
  check("subscriber slots released after disconnect",
    streamHealth.subscribers === 0, `subscribers=${streamHealth.subscribers}`);
  check("no frames dropped during the run",
    streamHealth.dropped_frames === 0, `dropped=${streamHealth.dropped_frames}`);

  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error("\nHARNESS ERROR:", err);
  process.exit(2);
});
