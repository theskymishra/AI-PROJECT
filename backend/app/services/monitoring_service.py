"""Phase 11: read-only response monitoring and adaptive replanning assessment."""
from __future__ import annotations

from app.models.common import AmbulanceStatus, EmergencyStatus
from app.models.monitoring import MonitoringItem, MonitoringResult, ResourceHealth
from app.services.planning_service import planning_service
from app.simulation.state import WorldState


class ResponseMonitoringService:
    """Derives operational health from the live simulation without mutating it."""

    def assess(self, state: WorldState, include_plan: bool = False) -> MonitoringResult:
        emergencies = [
            e for e in state.emergencies.values()
            if e.status not in {EmergencyStatus.RESOLVED, EmergencyStatus.UNRESOLVABLE}
        ]
        ambulances = list(state.ambulances.values())
        hospitals = list(state.hospitals.values())
        beds_available = sum(max(0, h.available_beds) for h in hospitals)
        beds_total = sum(max(0, h.total_beds) for h in hospitals)
        available_ambulances = sum(1 for a in ambulances if a.status == AmbulanceStatus.AVAILABLE)
        assigned = [e for e in emergencies if e.assigned_ambulance and e.assigned_hospital]

        items: list[MonitoringItem] = []
        alerts: list[str] = []
        recommendations: list[str] = []

        for emergency in emergencies:
            ambulance_id = emergency.assigned_ambulance
            hospital_id = emergency.assigned_hospital
            ambulance = state.ambulances.get(ambulance_id) if ambulance_id else None
            hospital = state.hospitals.get(hospital_id) if hospital_id else None
            attention = "STABLE"
            recommendation = "Continue current response plan."
            route_ready = ambulance is not None and hospital is not None

            if not ambulance_id or not hospital_id:
                attention = "UNASSIGNED"
                route_ready = False
                recommendation = "Run CSP allocation before execution."
                alerts.append(f"{emergency.id} has no complete resource assignment.")
            elif ambulance is None or hospital is None:
                attention = "INVALIDATED"
                route_ready = False
                recommendation = "Reallocate the affected emergency."
                alerts.append(f"{emergency.id} references a missing response resource.")
            elif emergency.status == EmergencyStatus.ALLOCATED:
                attention = "READY"
                recommendation = "Prepare or execute the HTN response plan."
            elif emergency.status in {EmergencyStatus.EN_ROUTE, EmergencyStatus.ON_SCENE, EmergencyStatus.TRANSPORTING}:
                attention = "ACTIVE"
                recommendation = "Monitor the next execution transition."

            if hospital is not None and hospital.available_beds <= max(1, emergency.patients):
                attention = "CAPACITY"
                recommendation = "Monitor hospital capacity and consider alternate allocation."
                alerts.append(f"{hospital.id} is approaching bed capacity for {emergency.id}.")

            items.append(
                MonitoringItem(
                    emergency_id=emergency.id,
                    status=emergency.status.value,
                    ambulance_id=ambulance_id,
                    hospital_id=hospital_id,
                    severity=getattr(emergency, "severity", None),
                    patients=int(getattr(emergency, "patients", 0)),
                    route_ready=route_ready,
                    attention=attention,
                    recommendation=recommendation,
                )
            )

        if available_ambulances == 0 and emergencies:
            alerts.append("No ambulances are currently available.")
            recommendations.append("Monitor completion of active transports before allocating new emergencies.")
        if beds_total and beds_available / beds_total <= 0.25 and emergencies:
            alerts.append("Hospital system is at or above the strained-capacity threshold.")
            recommendations.append("Prefer hospitals with greater remaining capacity during the next allocation.")
        if not emergencies:
            overall = "CLEAR"
            summary = "No unresolved emergencies require response monitoring."
        elif alerts:
            overall = "ATTENTION"
            summary = f"{len(emergencies)} active emergencies monitored; {len(alerts)} attention item(s) detected."
        else:
            overall = "STABLE"
            summary = f"{len(emergencies)} active emergencies are assigned and progressing normally."

        plan_status = "NOT_REQUESTED"
        plan_length = 0
        if include_plan:
            plan = planning_service.plan(state)
            plan_status = plan.status
            plan_length = len(plan.actions)
            if plan.status == "FOUND":
                recommendations.append(f"Current HTN planner can produce {len(plan.actions)} executable action(s).")
            else:
                recommendations.append("No executable HTN plan exists for the current state; reallocation may be required.")

        return MonitoringResult(
            status="OK",
            tick=state.clock.tick,
            overall=overall,
            summary=summary,
            health=ResourceHealth(
                ambulances_available=available_ambulances,
                ambulances_total=len(ambulances),
                beds_available=beds_available,
                beds_total=beds_total,
                active_emergencies=len(emergencies),
                assigned_emergencies=len(assigned),
            ),
            items=items,
            alerts=alerts,
            recommendations=recommendations,
            replanning_required=any(not item.route_ready or item.attention in {"UNASSIGNED", "INVALIDATED"} for item in items),
            plan_length=plan_length,
            plan_status=plan_status,
        )


monitoring_service = ResponseMonitoringService()
