"""Phase 13: deterministic, read-only response evaluation."""
from __future__ import annotations

from app.models.common import EmergencyStatus
from app.models.evaluation import EvaluationMetric, EvaluationResult
from app.services.monitoring_service import monitoring_service
from app.services.planning_service import planning_service
from app.simulation.state import WorldState


class ResponseEvaluationService:
    """Evaluates current response readiness without changing simulation state."""

    def assess(self, state: WorldState, include_plan: bool = True) -> EvaluationResult:
        emergencies = list(state.emergencies.values())
        active = [e for e in emergencies if e.status not in {EmergencyStatus.RESOLVED, EmergencyStatus.UNRESOLVABLE}]
        resolved = sum(e.status == EmergencyStatus.RESOLVED for e in emergencies)
        unresolvable = sum(e.status == EmergencyStatus.UNRESOLVABLE for e in emergencies)
        assigned = sum(bool(e.assigned_ambulance and e.assigned_hospital) for e in active)
        unassigned = len(active) - assigned

        ambulances = list(state.ambulances.values())
        hospitals = list(state.hospitals.values())
        ambulance_available = sum(bool(getattr(a, "available", False)) for a in ambulances)
        beds_available = sum(max(0, int(getattr(h, "beds_available", 0))) for h in hospitals)
        beds_total = sum(max(0, int(getattr(h, "total_beds", 0))) for h in hospitals)
        audit_events = len(state.timeline)

        monitoring = monitoring_service.assess(state, include_plan=False)
        replanning_required = bool(monitoring.replanning_required)

        coverage = 1.0 if not active else assigned / len(active)
        ambulance_utilization = 0.0 if not ambulances else 1.0 - (ambulance_available / len(ambulances))
        bed_utilization = 0.0 if not beds_total else 1.0 - (beds_available / beds_total)

        if unassigned > 0 or replanning_required:
            readiness = "ATTENTION"
        elif active:
            readiness = "READY"
        else:
            readiness = "STANDBY"

        recommendations: list[str] = []
        if unassigned:
            recommendations.append(f"Allocate resources for {unassigned} active emergency(ies) before execution.")
        if replanning_required:
            recommendations.append("Run the Phase 11 replanning assessment before continuing the current response.")
        if active and coverage == 1.0 and not replanning_required:
            recommendations.append("Current assignments are covered; continue monitoring and execute the generated HTN plan.")
        if not recommendations:
            recommendations.append("No immediate response changes are indicated by the current simulation state.")

        metrics = [
    EvaluationMetric(
        name="Assignment coverage",
        value=coverage * 100.0,
        unit="%",
        interpretation="Share of active emergencies with complete ambulance and hospital assignments.",
    ),
    EvaluationMetric(
        name="Ambulance utilization",
        value=ambulance_utilization * 100.0,
        unit="%",
        interpretation="Share of the ambulance fleet currently unavailable.",
    ),
    EvaluationMetric(
        name="Hospital bed utilization",
        value=bed_utilization * 100.0,
        unit="%",
        interpretation="Share of total hospital beds currently occupied or reserved.",
    ),
    EvaluationMetric(
        name="Audit events",
        value=float(audit_events),
        unit="events",
        interpretation="Recorded simulation timeline events available to the explainability layer.",
    ),
]

        plan_status = "NOT_REQUESTED"
        plan_length = 0
        if include_plan:
            plan = planning_service.plan(state)
            plan_status = plan.status
            plan_length = len(plan.actions)

        scenario = str(getattr(getattr(state, "scenario", None), "value", getattr(state, "scenario", "UNKNOWN")))
        return EvaluationResult(
            status="OK",
            tick=state.clock.tick,
            scenario=scenario,
            summary=(
                f"Evaluated the current {scenario} response at tick {state.clock.tick}: "
                f"{len(active)} active emergency(ies), {coverage * 100:.0f}% assignment coverage."
            ),
            readiness=readiness,
            metrics=metrics,
            recommendations=recommendations,
            active_emergencies=len(active),
            resolved_emergencies=resolved,
            unresolvable_emergencies=unresolvable,
            assigned_emergencies=assigned,
            unassigned_emergencies=unassigned,
            ambulances_available=ambulance_available,
            ambulances_total=len(ambulances),
            beds_available=beds_available,
            beds_total=beds_total,
            audit_events=audit_events,
            plan_status=plan_status,
            plan_length=plan_length,
        )


evaluation_service = ResponseEvaluationService()
