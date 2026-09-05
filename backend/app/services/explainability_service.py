"""Phase 12: deterministic, read-only explanations of AI decisions."""
from __future__ import annotations

from app.models.common import EmergencyStatus
from app.models.explainability import DecisionStep, EmergencyExplanation, ExplainabilityResult
from app.services.monitoring_service import monitoring_service
from app.services.planning_service import planning_service
from app.simulation.state import WorldState


class DecisionExplainabilityService:
    """Explains the current AI decision chain without mutating simulation state."""

    def build_report(self, state: WorldState, include_plan: bool = True) -> ExplainabilityResult:
        active = [
            e for e in state.emergencies.values()
            if e.status not in {EmergencyStatus.RESOLVED, EmergencyStatus.UNRESOLVABLE}
        ]
        monitor = monitoring_service.assess(state, include_plan=False)
        by_id = {item.emergency_id: item for item in monitor.items}
        explanations: list[EmergencyExplanation] = []

        for emergency in active:
            monitor_item = by_id.get(emergency.id)
            ambulance_id = emergency.assigned_ambulance
            hospital_id = emergency.assigned_hospital
            steps: list[DecisionStep] = []

            steps.append(
                DecisionStep(
                    component="SENSING / INFERENCE",
                    decision="Assess emergency state",
                    rationale="The simulation represents uncertain observations through its existing inference and evidence-fusion pipeline.",
                    evidence=[
                        f"severity={getattr(emergency, 'severity', None) or 'UNKNOWN'}",
                        f"patients={int(getattr(emergency, 'patients', 0))}",
                        f"status={emergency.status.value}",
                    ],
                )
            )

            if ambulance_id and hospital_id:
                decision = f"Keep assignment {ambulance_id} -> {hospital_id}"
                rationale = "A complete ambulance and hospital assignment exists in the current simulation state."
                evidence = [f"ambulance={ambulance_id}", f"hospital={hospital_id}"]
            else:
                decision = "Request resource allocation"
                rationale = "The emergency does not have a complete assignment, so execution should not proceed."
                evidence = ["complete_assignment=false"]

            steps.append(
                DecisionStep(
                    component="CSP ALLOCATION",
                    decision=decision,
                    rationale=rationale,
                    evidence=evidence,
                )
            )

            if ambulance_id and hospital_id:
                steps.append(
                    DecisionStep(
                        component="HTN PLANNING",
                        decision="Generate standard emergency response hierarchy",
                        rationale="The planner decomposes the assigned emergency into dispatch, load, transport, and handoff actions.",
                        evidence=["goal=RESCUE_ALL_ASSIGNED_EMERGENCIES"],
                    )
                )
                steps.append(
                    DecisionStep(
                        component="MONITORING",
                        decision=monitor_item.attention if monitor_item else "CHECK",
                        rationale=(monitor_item.recommendation if monitor_item else "Current response state requires assessment."),
                        evidence=[
                            f"route_ready={monitor_item.route_ready if monitor_item else False}",
                            f"replanning_required={monitor.replanning_required}",
                        ],
                    )
                )

            explanations.append(
                EmergencyExplanation(
                    emergency_id=emergency.id,
                    status=emergency.status.value,
                    severity=getattr(emergency, "severity", None),
                    patients=int(getattr(emergency, "patients", 0)),
                    ambulance_id=ambulance_id,
                    hospital_id=hospital_id,
                    decision=("CONTINUE CURRENT RESPONSE" if ambulance_id and hospital_id else "ALLOCATE RESOURCES"),
                    rationale=(
                        monitor_item.recommendation
                        if monitor_item
                        else "No monitoring record is available for this emergency."
                    ),
                    steps=steps,
                )
            )

        plan_status = "NOT_REQUESTED"
        plan_length = 0
        if include_plan:
            plan = planning_service.plan(state)
            plan_status = plan.status
            plan_length = len(plan.actions)

        return ExplainabilityResult(
            status="OK",
            tick=state.clock.tick,
            summary=f"Generated a read-only decision explanation for {len(active)} active emergency(ies).",
            ai_chain=["SENSING / INFERENCE", "CSP ALLOCATION", "HTN PLANNING", "HTN EXECUTION", "RESPONSE MONITORING"],
            explanations=explanations,
            audit_events=len(state.timeline),
            plan_status=plan_status,
            plan_length=plan_length,
        )


explainability_service = DecisionExplainabilityService()
