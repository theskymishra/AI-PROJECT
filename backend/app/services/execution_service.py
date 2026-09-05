"""Phase 10 execution engine for the deterministic HTN response plan.

Phase 8 creates a symbolic HTN plan. Phase 10 is the bridge from that plan to
live simulation state. Execution is deliberately explicit and stepwise so the
academic UI can demonstrate every transition and so a bad/stale action cannot
silently mutate unrelated resources.
"""
from __future__ import annotations

from threading import RLock
from time import perf_counter

from app.models.common import AmbulanceStatus, EmergencyStatus
from app.models.events import Alert, TimelineEntry
from app.models.execution import ExecutionResult
from app.models.planning import PlanAction
from app.services.planning_service import planning_service
from app.simulation.engine import SimulationEngine
from app.simulation.state import WorldState


class ExecutionError(ValueError):
    """Raised when a plan cannot safely be executed against current state."""


class PlanExecutionService:
    """Owns an in-memory execution cursor for the process-wide simulation."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._plan: list[PlanAction] = []
        self._cursor = 0
        self._signature: tuple[tuple[str, str, str], ...] = ()

    def _assignment_signature(self, state: WorldState) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            sorted(
                (
                    e.id,
                    str(e.assigned_ambulance),
                    str(e.assigned_hospital),
                )
                for e in state.emergencies.values()
                if e.assigned_ambulance and e.assigned_hospital
                and e.status not in {EmergencyStatus.RESOLVED, EmergencyStatus.UNRESOLVABLE}
            )
        )

    def prepare(self, state: WorldState) -> ExecutionResult:
        with self._lock:
            result = planning_service.plan(state)
            self._plan = list(result.actions)
            self._cursor = 0
            self._signature = self._assignment_signature(state)
            if result.status != "FOUND":
                return self._result(state, "NO_PLAN", "No executable HTN plan is available.")
            return self._result(state, "READY", f"Plan prepared with {len(self._plan)} actions.")

    def reset_cursor(self, state: WorldState) -> ExecutionResult:
        with self._lock:
            self._plan = []
            self._cursor = 0
            self._signature = ()
            return self._result(state, "IDLE", "Execution session cleared. Simulation state was not reset.")

    def execute_next(self, engine: SimulationEngine) -> ExecutionResult:
        with self._lock:
            state = engine.state
            if not self._plan:
                prepared = self.prepare(state)
                if prepared.status != "READY":
                    return prepared

            self._ensure_plan_current(state)
            if self._cursor >= len(self._plan):
                return self._result(state, "COMPLETED", "All planned actions have been executed.")

            action = self._plan[self._cursor]
            self._apply_action(state, action)
            self._cursor += 1
            self._record_execution(state, action)
            status = "COMPLETED" if self._cursor == len(self._plan) else "RUNNING"
            result = self._result(state, status, f"Executed action {self._cursor}/{len(self._plan)}: {action.name}.", action)
            self._publish(engine, action, result)
            return result

    def execute_all(self, engine: SimulationEngine) -> ExecutionResult:
        with self._lock:
            if not self._plan:
                prepared = self.prepare(engine.state)
                if prepared.status != "READY":
                    return prepared
            last: PlanAction | None = None
            while self._cursor < len(self._plan):
                self._ensure_plan_current(engine.state)
                last = self._plan[self._cursor]
                self._apply_action(engine.state, last)
                self._cursor += 1
                self._record_execution(engine.state, last)
            result = self._result(engine.state, "COMPLETED", f"Executed all {len(self._plan)} planned actions.", last)
            if last is not None:
                self._publish(engine, last, result)
            return result

    def _ensure_plan_current(self, state: WorldState) -> None:
        if self._signature != self._assignment_signature(state):
            raise ExecutionError("The plan is stale because resource assignments changed. Prepare a new plan.")

    def _apply_action(self, state: WorldState, action: PlanAction) -> None:
        if action.name == "DISPATCH_AMBULANCE":
            ambulance_id, emergency_id = action.args
            ambulance = state.ambulances.get(ambulance_id)
            emergency = state.emergencies.get(emergency_id)
            if ambulance is None or emergency is None:
                raise ExecutionError("Dispatch references a missing ambulance or emergency.")
            if emergency.assigned_ambulance != ambulance.id:
                raise ExecutionError("Dispatch assignment no longer matches the current allocation.")
            # Phase 7 already marks the allocated ambulance DISPATCHED. Phase 10
            # advances the allocated emergency into the operational EN_ROUTE state.
            if ambulance.status not in {AmbulanceStatus.DISPATCHED, AmbulanceStatus.AVAILABLE}:
                raise ExecutionError(f"Ambulance {ambulance.id} is not dispatchable from {ambulance.status.value}.")
            ambulance.status = AmbulanceStatus.EN_ROUTE
            emergency.status = EmergencyStatus.EN_ROUTE
            return

        if action.name == "LOAD_PATIENTS":
            ambulance_id, emergency_id = action.args
            ambulance = state.ambulances.get(ambulance_id)
            emergency = state.emergencies.get(emergency_id)
            if ambulance is None or emergency is None:
                raise ExecutionError("Load references a missing ambulance or emergency.")
            if ambulance.assigned_emergency != emergency.id:
                raise ExecutionError("Ambulance is not assigned to this emergency.")
            if emergency.status != EmergencyStatus.EN_ROUTE:
                raise ExecutionError("Patients can only be loaded after dispatch.")
            ambulance.status = AmbulanceStatus.AT_SCENE
            ambulance.node_id = emergency.node_id
            emergency.status = EmergencyStatus.ON_SCENE
            return

        if action.name == "TRANSPORT_TO_HOSPITAL":
            ambulance_id, emergency_id, hospital_id = action.args
            ambulance = state.ambulances.get(ambulance_id)
            emergency = state.emergencies.get(emergency_id)
            hospital = state.hospitals.get(hospital_id)
            if ambulance is None or emergency is None or hospital is None:
                raise ExecutionError("Transport references a missing resource.")
            if emergency.assigned_hospital != hospital.id or ambulance.assigned_emergency != emergency.id:
                raise ExecutionError("Transport assignment no longer matches the current plan.")
            if emergency.status != EmergencyStatus.ON_SCENE or ambulance.status != AmbulanceStatus.AT_SCENE:
                raise ExecutionError("Transport requires the ambulance and emergency to be at the scene.")
            ambulance.status = AmbulanceStatus.TRANSPORTING
            ambulance.node_id = hospital.node_id
            ambulance.position = None
            emergency.status = EmergencyStatus.TRANSPORTING
            return

        if action.name == "HANDOFF_PATIENTS":
            emergency_id, hospital_id = action.args
            emergency = state.emergencies.get(emergency_id)
            hospital = state.hospitals.get(hospital_id)
            if emergency is None or hospital is None:
                raise ExecutionError("Handoff references a missing emergency or hospital.")
            ambulance = state.ambulances.get(emergency.assigned_ambulance) if emergency.assigned_ambulance else None
            if emergency.assigned_hospital != hospital.id:
                raise ExecutionError("Handoff hospital no longer matches the allocation.")
            if emergency.status != EmergencyStatus.TRANSPORTING:
                raise ExecutionError("Handoff requires an emergency currently in transport.")
            if hospital.status.value == "FULL":
                # Phase 7 reserves beds when allocation is applied. No second bed
                # decrement happens here; this check prevents a newly-full hospital
                # from accepting a plan that was invalidated externally.
                raise ExecutionError(f"Hospital {hospital.id} is full; handoff is invalidated.")
            emergency.status = EmergencyStatus.RESOLVED
            if ambulance is not None:
                ambulance.status = AmbulanceStatus.AVAILABLE
                ambulance.assigned_emergency = None
                ambulance.position = None
                ambulance.node_id = hospital.node_id
            return

        raise ExecutionError(f"Unsupported plan action: {action.name}")

    def _record_execution(self, state: WorldState, action: PlanAction) -> None:
        tick = state.clock.tick
        seq = state.next_seq()
        emergency_id = next((arg for arg in action.args if arg.startswith("E")), "")
        state.add_timeline(
            TimelineEntry(
                id=f"EXEC-{seq}",
                tick=tick,
                category="AI_EXECUTION",
                headline=f"Executed {action.name}",
                detail=f"HTN action executed for {emergency_id or 'current response plan'}.",
                ai_components=["HTN", "PLAN_EXECUTION"],
            )
        )

    def _publish(self, engine: SimulationEngine, action: PlanAction, result: ExecutionResult) -> None:
        # A full snapshot is intentional here: ambulance status and emergency
        # status are both changed by one execution action, and a snapshot keeps
        # every existing frontend reducer consistent.
        engine.broadcaster.publish(
            seq=engine.state.next_seq(),
            tick=engine.state.clock.tick,
            type="plan",
            payload={
                "action": action.model_dump(),
                "execution": result.model_dump(exclude={"snapshot"}),
                "snapshot": engine.snapshot(),
            },
        )

    def _result(
        self,
        state: WorldState,
        status: str,
        message: str,
        last_action: PlanAction | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            status=status,
            message=message,
            plan=list(self._plan),
            next_action_index=self._cursor if self._cursor < len(self._plan) else None,
            executed_count=self._cursor,
            total_actions=len(self._plan),
            last_action=last_action,
            tick=state.clock.tick,
            snapshot={
                "stats": state.stats(),
                "emergencies": [e.model_dump() for e in state.emergencies.values()],
                "ambulances": [a.model_dump() for a in state.ambulances.values()],
                "hospitals": [h.model_dump() for h in state.hospitals.values()],
            },
        )


execution_service = PlanExecutionService()
