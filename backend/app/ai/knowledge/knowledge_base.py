"""Construction of the Phase 6 knowledge base from live simulation state."""

from __future__ import annotations

from app.ai.knowledge.engine import Fact, KnowledgeEngine, Rule
from app.ai.knowledge.parser import Atom
from app.config import KNOWLEDGE_HIGH_FAILURE_THRESHOLD
from app.models.common import AmbulanceStatus, EmergencyStatus, HospitalStatus, ShelterStatus
from app.simulation.state import WorldState


def F(predicate: str, *args: str) -> Fact:
    return Atom(predicate, tuple(args))


def build_knowledge_base(state: WorldState) -> KnowledgeEngine:
    """Translate current numeric/state data into symbolic facts and rules."""
    facts: list[Fact] = []

    # World and road facts.
    for road in state.roads.values():
        facts.append(F("Road", road.id))
        facts.append(F("Connects", road.id, road.source, road.destination))
        facts.append(F("Elevation", road.id, str(road.elevation_band)))
        if road.blocked:
            facts.append(F("Blocked", road.id))
        if road.failure_probability >= KNOWLEDGE_HIGH_FAILURE_THRESHOLD:
            facts.append(F("HighFailureProb", road.id))
        if road.status.value == "RISKY":
            facts.append(F("Risky", road.id))

    # Facilities and fleet facts.
    for hospital in state.hospitals.values():
        facts.append(F("Hospital", hospital.id))
        facts.append(F("At", hospital.id, hospital.node_id))
        facts.append(F("HospitalBeds", hospital.id, str(hospital.available_beds)))
        if hospital.status is not HospitalStatus.FULL:
            facts.append(F("OpenHospital", hospital.id))
        if hospital.available_icu > 0:
            facts.append(F("ICUAvailable", hospital.id))

    for shelter in state.shelters.values():
        facts.append(F("Shelter", shelter.id))
        facts.append(F("At", shelter.id, shelter.node_id))
        if shelter.status is not ShelterStatus.FULL:
            facts.append(F("OpenShelter", shelter.id))
        if shelter.safety_score >= 0.8:
            facts.append(F("SafeShelter", shelter.id))

    for ambulance in state.ambulances.values():
        facts.append(F("Ambulance", ambulance.id))
        facts.append(F("At", ambulance.id, ambulance.node_id))
        facts.append(F("Capacity", ambulance.id, str(ambulance.capacity)))
        if ambulance.status is AmbulanceStatus.AVAILABLE:
            facts.append(F("AvailableAmbulance", ambulance.id))

    for emergency in state.emergencies.values():
        facts.extend(
            [
                F("Emergency", emergency.id),
                F("At", emergency.id, emergency.node_id),
                F("Severity", emergency.id, str(emergency.severity)),
                F("Patients", emergency.id, str(emergency.patients)),
            ]
        )
        if emergency.status not in {EmergencyStatus.RESOLVED, EmergencyStatus.UNRESOLVABLE}:
            facts.append(F("ActiveEmergency", emergency.id))
        if emergency.medical_priority >= 4:
            facts.append(F("HighPriority", emergency.id))
        if emergency.patients >= 1:
            facts.append(F("NeedsTransport", emergency.id))

    rules = (
        Rule(
            "high_failure_implies_unsafe",
            (F("HighFailureProb", "R"),),
            F("Unsafe", "R"),
        ),
        Rule(
            "blocked_road_is_unsafe",
            (F("Blocked", "R"),),
            F("Unsafe", "R"),
        ),
        Rule(
            "unsafe_road_should_be_avoided",
            (F("Unsafe", "R"),),
            F("Avoid", "R"),
        ),
        Rule(
            "critical_active_emergency_needs_priority",
            (
                F("ActiveEmergency", "E"),
                F("Severity", "E", "CRITICAL"),
            ),
            F("PriorityRescue", "E"),
        ),
        Rule(
            "high_priority_active_emergency_needs_priority",
            (
                F("ActiveEmergency", "E"),
                F("HighPriority", "E"),
            ),
            F("PriorityRescue", "E"),
        ),
        Rule(
            "open_hospital_is_candidate",
            (F("OpenHospital", "H"), F("HospitalBeds", "H", "B")),
            F("CandidateHospital", "H"),
        ),
        Rule(
            "safe_open_shelter_is_candidate",
            (F("OpenShelter", "S"), F("SafeShelter", "S")),
            F("CandidateShelter", "S"),
        ),
    )
    return KnowledgeEngine(facts=facts, rules=rules)
