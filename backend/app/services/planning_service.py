"""Phase 8 hierarchical task-network planning for emergency response.

The planner is deliberately deterministic and state-based.  Phase 7 decides
*which* ambulance and hospital should serve an emergency; Phase 8 turns those
assignments into an ordered rescue plan.  It does not mutate simulation state.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from app.models.common import EmergencyStatus
from app.models.planning import PlanAction, PlanNode, PlanResult
from app.simulation.state import WorldState


@dataclass(frozen=True, slots=True)
class Task:
    name: str
    args: tuple[str, ...] = ()


class HTNPlanner:
    """Small deterministic HTN planner with explicit preconditions/effects."""

    GOAL = "RESCUE_ALL_ASSIGNED_EMERGENCIES"

    def plan(self, state: WorldState) -> PlanResult:
        started = perf_counter()
        nodes_expanded = 0

        emergencies = sorted(
            (
                e
                for e in state.emergencies.values()
                if e.status not in {EmergencyStatus.RESOLVED, EmergencyStatus.UNRESOLVABLE}
                and e.assigned_ambulance is not None
                and e.assigned_hospital is not None
            ),
            key=lambda e: (-e.medical_priority, -e.waiting_ticks, e.id),
        )

        hierarchy_children: list[PlanNode] = []
        actions: list[PlanAction] = []

        for emergency in emergencies:
            nodes_expanded += 1
            ambulance = state.ambulances.get(emergency.assigned_ambulance)
            hospital = state.hospitals.get(emergency.assigned_hospital)
            if ambulance is None or hospital is None:
                return self._no_plan(started, nodes_expanded, f"missing_resource:{emergency.id}")

            # Decompose RESCUE(E) -> DISPATCH -> LOAD -> TRANSPORT -> HANDOFF.
            primitive_tasks = [
                Task("DISPATCH", (emergency.id, ambulance.id)),
                Task("LOAD_PATIENTS", (emergency.id, ambulance.id)),
                Task("TRANSPORT", (emergency.id, ambulance.id, hospital.id)),
                Task("HANDOFF", (emergency.id, hospital.id)),
            ]
            hierarchy_children.append(
                PlanNode(
                    task=f"RESCUE({emergency.id})",
                    method="STANDARD_EMERGENCY_RESPONSE",
                    primitive=False,
                    children=[
                        PlanNode(task=f"{task.name}({', '.join(task.args)})", method=None, primitive=True)
                        for task in primitive_tasks
                    ],
                )
            )

            actions.extend(self._actions_for(emergency.id, ambulance.id, hospital.id))

        if not emergencies:
            return self._no_plan(started, nodes_expanded, "no_assigned_emergencies")

        hierarchy = PlanNode(
            task=self.GOAL,
            method="RESCUE_EACH_ASSIGNED_EMERGENCY",
            primitive=False,
            children=hierarchy_children,
        )

        return PlanResult(
            status="FOUND",
            goal=self.GOAL,
            actions=actions,
            hierarchy=hierarchy,
            plan_length=len(actions),
            nodes_expanded=nodes_expanded,
            execution_ms=round((perf_counter() - started) * 1000, 4),
            invalidated_step=None,
        )

    def _actions_for(self, emergency_id: str, ambulance_id: str, hospital_id: str) -> list[PlanAction]:
        return [
            PlanAction(
                name="DISPATCH_AMBULANCE",
                args=[ambulance_id, emergency_id],
                preconditions=[f"Available({ambulance_id})", f"Assigned({emergency_id},{ambulance_id})"],
                add_effects=[f"Dispatched({ambulance_id})"],
                delete_effects=[f"Available({ambulance_id})"],
            ),
            PlanAction(
                name="LOAD_PATIENTS",
                args=[ambulance_id, emergency_id],
                preconditions=[f"Dispatched({ambulance_id})", f"Patients({emergency_id})"],
                add_effects=[f"Loaded({ambulance_id},{emergency_id})"],
                delete_effects=[f"Waiting({emergency_id})"],
            ),
            PlanAction(
                name="TRANSPORT_TO_HOSPITAL",
                args=[ambulance_id, emergency_id, hospital_id],
                preconditions=[
                    f"Loaded({ambulance_id},{emergency_id})",
                    f"AssignedHospital({emergency_id},{hospital_id})",
                ],
                add_effects=[f"AtHospital({emergency_id},{hospital_id})"],
                delete_effects=[f"AtScene({emergency_id})"],
            ),
            PlanAction(
                name="HANDOFF_PATIENTS",
                args=[emergency_id, hospital_id],
                preconditions=[f"AtHospital({emergency_id},{hospital_id})", f"Open({hospital_id})"],
                add_effects=[f"Treated({emergency_id})"],
                delete_effects=[f"AwaitingTreatment({emergency_id})"],
            ),
        ]

    @staticmethod
    def _no_plan(started: float, nodes_expanded: int, reason: str) -> PlanResult:
        return PlanResult(
            status="NO_PLAN",
            goal=HTNPlanner.GOAL,
            actions=[],
            hierarchy=None,
            plan_length=0,
            nodes_expanded=nodes_expanded,
            execution_ms=round((perf_counter() - started) * 1000, 4),
            invalidated_step=None,
        )


planning_service = HTNPlanner()
