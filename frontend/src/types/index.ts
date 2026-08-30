/**
 * FROZEN CONTRACT (Phase 1).
 *
 * This file mirrors backend/app/models/. Any change to a shape here must be
 * made in the same commit as the corresponding change in the Pydantic models,
 * and agreed by all three team members (Phase 0 section 12).
 *
 * Agreement between the two files is enforced by review, not by tooling. That
 * is a deliberate trade-off: schema-generation tooling would be a fourth thing
 * to maintain on a three-person project.
 *
 * Most of these types have no consumer in Phase 1. That is the point. Freezing
 * the contract now is what lets frontend work proceed in parallel with backend
 * work instead of waiting for it.
 */

/* ==========================================================================
   Identifier aliases
   ========================================================================== */

export type NodeId = string;
export type ZoneId = string;
export type RoadId = string;
export type EmergencyId = string;
export type AmbulanceId = string;
export type HospitalId = string;
export type ShelterId = string;
export type SensorId = string;
export type AlertId = string;

/* ==========================================================================
   World constants (mirror of app/models/common.py)
   ========================================================================== */

/** Largest ambulance capacity in the fleet. Emergency.patients is clamped here. */
export const MAX_AMBULANCE_CAPACITY = 4;
export const MIN_MEDICAL_PRIORITY = 1;
export const MAX_MEDICAL_PRIORITY = 5;

/* ==========================================================================
   Enums (string unions; the wire format is the string itself)
   ========================================================================== */

export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type EmergencyStatus =
  | "REPORTED"
  | "ALLOCATED"
  | "EN_ROUTE"
  | "ON_SCENE"
  | "TRANSPORTING"
  | "RESOLVED"
  | "UNRESOLVABLE";

export type AmbulanceStatus =
  | "AVAILABLE"
  | "DISPATCHED"
  | "EN_ROUTE"
  | "AT_SCENE"
  | "TRANSPORTING"
  | "BUSY";

/** Derived from Road.blocked and Road.failureProbability, never stored raw. */
export type RoadStatus = "SAFE" | "RISKY" | "BLOCKED";

/** Hidden state space of the HMM; domain of the BN FloodSeverity node. */
export type FloodState = "NORMAL" | "RISING" | "HIGH" | "CRITICAL";

/** HMM observation alphabet. Emitted with noise, never read off the true state. */
export type Observation =
  | "LOW_WATER"
  | "MEDIUM_WATER"
  | "HIGH_WATER"
  | "RAPIDLY_RISING";

export type SimStatus = "IDLE" | "RUNNING" | "PAUSED" | "COMPLETED";
export type NodeKind = "JUNCTION" | "FACILITY";
export type ElevationBand = "LOW" | "MED" | "HIGH";
export type HospitalStatus = "OPEN" | "STRAINED" | "FULL";
export type ShelterStatus = "OPEN" | "NEAR_FULL" | "FULL";
export type AlertLevel = "INFO" | "WARNING" | "CRITICAL";

/* ==========================================================================
   System (Phase 1 -- the only shapes with a live producer today)
   ========================================================================== */

export interface HealthResponse {
  status: "ok";
  app: string;
  full_name: string;
  tagline: string;
  version: string;
  phase: number;
  total_phases: number;
  uptime_seconds: number;
}

/* ==========================================================================
   World entities
   ========================================================================== */

export interface Position {
  x: number;
  y: number;
}

export interface WorldNode {
  id: NodeId;
  name: string;
  x: number;
  y: number;
  zone_id: ZoneId;
  kind: NodeKind;
}

export interface Zone {
  id: ZoneId;
  name: string;
  polygon: Array<[number, number]>;
  population: number;
  flood_level: number;
  elevation: number;
  elevation_band: ElevationBand;
}

export interface Road {
  id: RoadId;
  source: NodeId;
  destination: NodeId;
  /** Road length in kilometres. Invariant W1: >= geometric_length. */
  distance: number;
  /** SCALE_KM_PER_UNIT * euclid(source, destination), in kilometres. */
  geometric_length: number;
  detour_factor: number;
  elevation_band: ElevationBand;
  flood_level: number;
  damage_level: number;
  /** P(RoadFailure = TRUE) from the Bayesian Network. */
  failure_probability: number;
  /** Composite display-only figure. Never an input to A*. */
  risk_score: number;
  blocked: boolean;
  /**
   * Derived server-side via @computed_field, not stored.
   * Serialised deliberately: the map renders road state, and reimplementing
   * the RISKY threshold in TypeScript would put one rule in two languages
   * where they can silently drift apart.
   */
  status: RoadStatus;
}

export interface Emergency {
  id: EmergencyId;
  node_id: NodeId;
  zone_id: ZoneId;
  severity: Severity;
  /** Total people at the scene. Drives evacuation and shelter figures. */
  people_affected: number;
  /**
   * Subset of people_affected requiring ambulance transport.
   * patients = clamp(min(people_affected, 1 + medical_priority / 2), 1, 4)
   * The CSP capacity constraint binds against this field, not people_affected.
   */
  patients: number;
  medical_priority: number;
  reported_at_tick: number;
  waiting_ticks: number;
  status: EmergencyStatus;
  assigned_ambulance: AmbulanceId | null;
  assigned_hospital: HospitalId | null;
}

export interface EdgePosition {
  road_id: RoadId;
  /** 0 at source, 1 at destination. */
  progress: number;
}

export interface Ambulance {
  id: AmbulanceId;
  node_id: NodeId;
  position: EdgePosition | null;
  capacity: number;
  speed_kmh: number;
  status: AmbulanceStatus;
  assigned_emergency: EmergencyId | null;
}

export interface Hospital {
  id: HospitalId;
  name: string;
  node_id: NodeId;
  total_beds: number;
  available_beds: number;
  total_icu: number;
  available_icu: number;
  /** Derived server-side. See the note on Road.status. */
  status: HospitalStatus;
  has_icu: boolean;
}

export interface Shelter {
  id: ShelterId;
  name: string;
  node_id: NodeId;
  capacity: number;
  occupancy: number;
  safety_score: number;
  /** Derived server-side. See the note on Road.status. */
  status: ShelterStatus;
}

export interface SensorReading {
  tick: number;
  sensor_id: SensorId;
  zone_id: ZoneId;
  rainfall_mm: number;
  water_level_m: number;
  river_level_m: number;
  observation: Observation;
}

/* ==========================================================================
   Events, alerts, timeline
   ========================================================================== */

export type EventType =
  | "RAINFALL_CHANGE"
  | "WATER_LEVEL_CHANGE"
  | "ROAD_BLOCKED"
  | "ROAD_RESTORED"
  | "ROAD_DAMAGE"
  | "EMERGENCY_CREATED"
  | "HOSPITAL_OVERLOAD"
  | "ROUTE_INVALIDATED"
  | "REPLANNING"
  | "ROUTE_UPDATED"
  | "ALLOCATION_UPDATED"
  | "PLAN_UPDATED"
  | "EMERGENCY_RESOLVED";

export type SSEEventType =
  | "snapshot"
  | "tick"
  | "sensors"
  | "belief"
  | "kb_delta"
  | "road_status"
  | "emergency"
  | "allocation"
  | "route"
  | "plan"
  | "alert"
  | "timeline"
  | "sim_control";

export interface SimEvent {
  /** Scheduled on an integer tick, never a wall-clock timestamp. */
  tick: number;
  type: EventType;
  payload: Record<string, unknown>;
}

export interface TimelineEntry {
  id: string;
  tick: number;
  category: string;
  headline: string;
  detail: string;
  /** Which AI subsystems produced this entry, e.g. ["HMM", "A*"]. */
  ai_components: string[];
}

export interface Alert {
  id: AlertId;
  tick: number;
  level: AlertLevel;
  title: string;
  message: string;
  source: string;
}

export interface SSEEnvelope {
  /** Monotonic per connection. A gap triggers a full state refetch. */
  seq: number;
  tick: number;
  type: SSEEventType;
  payload: Record<string, unknown>;
}

/* ==========================================================================
   AI result envelopes
   ========================================================================== */

export interface RouteResult {
  found: boolean;
  path: NodeId[];
  edges: RoadId[];
  /** Risk-weighted kilometres. */
  total_cost: number;
  /** Plain kilometres. */
  total_distance: number;
  nodes_generated: number;
  nodes_expanded: number;
  execution_ms: number;
  expansion_order: NodeId[];
  environment_version: number;
  failure_reason: string | null;
}

export interface CSPAssignment {
  ambulance_id: AmbulanceId;
  hospital_id: HospitalId;
}

export interface CSPTraceStep {
  step: number;
  variable: EmergencyId;
  value: string;
  outcome: "ASSIGN" | "REJECT" | "BACKTRACK" | "PRUNE";
  reason: string;
}

export interface CSPResult {
  status: "SOLVED" | "PARTIAL" | "UNSATISFIABLE";
  assignments: Record<EmergencyId, CSPAssignment>;
  /** Emergency id -> reason code. */
  unassigned: Record<EmergencyId, string>;
  constraints_checked: number;
  conflicts: number;
  backtracks: number;
  domain_reductions: number;
  execution_ms: number;
  trace: CSPTraceStep[];
}

export interface HMMResult {
  belief: Record<FloodState, number>;
  most_likely: FloodState;
  observation_history: Observation[];
  /** One row per tick, ordered as FloodState. */
  belief_history: number[][];
  execution_ms: number;
}

export interface BayesResult {
  query: string;
  probability: number;
  evidence: Record<string, string>;
  per_road: Record<RoadId, number>;
  marginals: Record<string, Record<string, number>>;
  used_hmm_virtual_evidence: boolean;
  execution_ms: number;
}

export interface InferenceStep {
  rule_name: string;
  bindings: Record<string, string>;
  premises: string[];
  conclusion: string;
}

export interface InferenceResult {
  initial_facts: string[];
  derived_facts: string[];
  steps: InferenceStep[];
  iterations: number;
  execution_ms: number;
}

export interface FOLResult {
  query: string;
  bindings: Array<Record<string, string>>;
  count: number;
  execution_ms: number;
}

export interface PlanAction {
  name: string;
  args: string[];
  preconditions: string[];
  add_effects: string[];
  delete_effects: string[];
}

export interface PlanNode {
  task: string;
  method: string | null;
  primitive: boolean;
  children: PlanNode[];
}

export interface PlanResult {
  status: "FOUND" | "NO_PLAN";
  goal: string;
  actions: PlanAction[];
  hierarchy: PlanNode | null;
  plan_length: number;
  nodes_expanded: number;
  execution_ms: number;
  invalidated_step: number | null;
}

/* ==========================================================================
   Phase 2 — simulation snapshot and stream payloads
   ========================================================================== */

export interface ClockState {
  tick: number;
  speed: number;
  status: SimStatus;
  /** Pre-formatted MM:SS. Formatted server-side so it cannot drift from tick. */
  elapsed_label: string;
}

export interface ScenarioInfo {
  name: string;
  label: string;
  description: string;
}

export interface ScenarioDetail extends ScenarioInfo {
  duration_ticks: number;
}

export interface EnvironmentState {
  rainfall_mm: number;
  water_level_m: number;
  river_level_m: number;
  /**
   * ENVIRONMENT GROUND TRUTH, not an AI output.
   *
   * The agent never observes this. Sensors emit noisy symbols drawn from
   * P(observation | true_flood_state); the Phase 5 HMM estimates this value
   * from those symbols. Displaying it beside the Phase 5 estimate is what
   * makes filtering lag visible. Never label it as an inference.
   */
  true_flood_state: FloodState;
  /** Route cache key component. Bumped only past RISK_EPSILON. */
  environment_version: number;
}

export interface SimulationStats {
  active_emergencies: number;
  people_at_risk: number;
  patients_awaiting_transport: number;
  available_ambulances: number;
  total_ambulances: number;
  available_beds: number;
  total_beds: number;
  available_icu: number;
  blocked_roads: number;
  risky_roads: number;
  total_roads: number;
}

/** Full state, sent on SSE connect and by GET /api/simulation/state. */
export interface SimulationSnapshot {
  clock: ClockState;
  scenario: ScenarioDetail;
  available_scenarios: ScenarioInfo[];
  environment: EnvironmentState;
  stats: SimulationStats;
  nodes: WorldNode[];
  zones: Zone[];
  roads: Road[];
  emergencies: Emergency[];
  ambulances: Ambulance[];
  hospitals: Hospital[];
  shelters: Shelter[];
  sensors: SensorReading[];
  sensor_history: SensorReading[];
  timeline: TimelineEntry[];
  alerts: Alert[];
}

/**
 * Per-tick delta.
 *
 * READ THE MERGE SEMANTICS BEFORE CONSUMING THIS. Fields fall into three
 * categories and MUST be handled differently:
 *
 *   COMPLETE  clock, environment, stats, sensors, hospitals
 *             Always present, always the full set. Replace wholesale.
 *
 *   PARTIAL   roads, emergencies
 *             Present ONLY when something changed, and containing ONLY the
 *             changed entities -- typically 1 of 38 roads. MERGE BY ID.
 *             Replacing the local array with one of these deltas silently
 *             deletes every entity it does not mention.
 *
 *   TAIL      timeline_tail, alerts_tail
 *             Always present (empty array when nothing new), last 5 entries.
 *             Append with de-duplication by id; the same entries legitimately
 *             arrive twice across a reconnect.
 *
 * `ambulances` is deliberately absent: the backend does not send it on tick
 * frames in Phase 2. Ambulance movement arrives in Phase 10.
 */
export interface TickPayload {
  clock: ClockState;
  environment: EnvironmentState;
  stats: SimulationStats;
  sensors: SensorReading[];
  hospitals: Hospital[];
  timeline_tail: TimelineEntry[];
  alerts_tail: Alert[];
  /** PARTIAL delta -- merge by id, never replace. */
  roads?: Road[];
  /** PARTIAL delta -- merge by id, never replace. */
  emergencies?: Emergency[];
}

export interface SimControlPayload {
  action: string;
  snapshot: SimulationSnapshot;
}

/* ==========================================================================
   Phase 4 — A* routing
   ========================================================================== */

export interface RouteRequest {
  start: NodeId;
  goal: NodeId;
  /** Force a fresh search so expansion metrics reflect this call, not a hit. */
  use_cache?: boolean;
}

export interface RouteCacheStats {
  hits: number;
  misses: number;
  invalidations: number;
  entries: number;
  hit_rate: number;
}

/**
 * Cost weights, mirroring COST_WEIGHT_* in backend/app/config.py.
 *
 *     w(e) = distance * (1 + flood*flood_level + damage*damage_level
 *                          + failure*P_fail)
 *
 * NOTE: `failure` multiplies road.failure_probability, which is 0.0 on every
 * road until the Bayesian Network arrives in Phase 5. Routing today is flood-
 * and damage-aware only.
 */
export interface RouteCostWeights {
  flood: number;
  damage: number;
  failure: number;
}

export interface RouteResponse {
  route: RouteResult;
  cache: RouteCacheStats;
  weights: RouteCostWeights;
}

/* ==========================================================================
   Phase 5 — HMM and Bayesian Network
   ========================================================================== */

export interface HMMRequest {
  /**
   * Optional sequence to filter from the prior. Omit to read the LIVE filter.
   * Supplying one runs a throwaway filter and never disturbs the live belief.
   */
  observations?: Observation[];
}

export interface HMMResponse {
  belief: Record<FloodState, number>;
  most_likely: FloodState;
  /** Shannon entropy in bits, 0 (certain) to 2 (uniform over four states). */
  entropy: number;
  /** P(o_t | o_1..o_t-1). Sustained low values mean the model is surprised. */
  step_likelihood: number;
  observation_history: Observation[];
  /** One row per tick, ordered as `states`. */
  belief_history: number[][];
  states: FloodState[];
  live: boolean;
  execution_ms: number;
}

export type EvidenceBand = "LOW" | "MED" | "HIGH";

export interface BayesianRequest {
  rainfall?: EvidenceBand;
  water_level?: EvidenceBand;
  /**
   * False detaches the HMM's virtual evidence, leaving the
   * Rainfall -> WaterLevel -> FloodSeverity chain to speak for itself.
   */
  use_hmm?: boolean;
}

export interface RiskiestRoad {
  road_id: RoadId;
  probability: number;
  elevation_band: ElevationBand;
}

export interface BayesianResponse {
  flood_severity: Record<FloodState, number>;
  water_level: Record<EvidenceBand, number>;
  rainfall: Record<EvidenceBand, number>;
  per_road: Record<RoadId, number>;
  evidence: { Rainfall: EvidenceBand; WaterLevel: EvidenceBand };
  used_hmm_virtual_evidence: boolean;
  execution_ms: number;
  riskiest_roads: RiskiestRoad[];
}
