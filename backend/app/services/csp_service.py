"""Phase 7 constraint-satisfaction resource allocator.

The allocator deliberately keeps the CSP small and inspectable for the academic
project. Variables are active emergencies; each domain value is an
(ambulance, hospital) pair that satisfies local capacity, availability and
A* reachability constraints. MRV chooses the next emergency, backtracking
searches alternatives, and forward checking prunes values that can no longer be
used after an assignment.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from app.ai.knowledge.knowledge_base import build_knowledge_base
from app.models.ai_result import CSPAssignment, CSPResult, CSPTraceStep
from app.models.common import AmbulanceStatus, EmergencyStatus, HospitalStatus
from app.services.routing_service import routing_service
from app.simulation.state import WorldState


@dataclass(frozen=True, slots=True)
class Candidate:
    ambulance_id: str
    hospital_id: str
    route_to_scene_cost: float
    route_to_hospital_cost: float


@dataclass(slots=True)
class SolveStats:
    constraints_checked: int = 0
    conflicts: int = 0
    backtracks: int = 0
    domain_reductions: int = 0
    step: int = 0


class CSPAllocator:
    """Deterministic CSP solver for emergency resource allocation."""

    def solve(self, state: WorldState) -> CSPResult:
        started = perf_counter()
        stats = SolveStats()
        trace: list[CSPTraceStep] = []

        kb = build_knowledge_base(state)
        inference = kb.infer()
        avoid = frozenset(
            fact.args[0] for fact in kb.facts if fact.predicate == "Avoid"
        )

        emergencies = [
            e for e in state.emergencies.values()
            if e.status not in {EmergencyStatus.RESOLVED, EmergencyStatus.UNRESOLVABLE}
            and e.assigned_ambulance is None
        ]
        emergencies.sort(key=lambda e: (-e.medical_priority, -e.waiting_ticks, e.id))

        if not emergencies:
            return CSPResult(
                status="SOLVED",
                assignments={},
                unassigned={},
                execution_ms=round((perf_counter() - started) * 1000, 4),
                trace=[],
            )

        domains: dict[str, list[Candidate]] = {}
        unassigned: dict[str, str] = {}
        for emergency in emergencies:
            domain = self._build_domain(state, emergency, avoid, stats, trace)
            domains[emergency.id] = domain
            if not domain:
                unassigned[emergency.id] = "NO_VALID_ASSIGNMENT"

        # Keep the original domain snapshot so an unsatisfied variable can be
        # explained even after forward checking has reduced later domains.
        original_domains = {key: list(value) for key, value in domains.items()}

        assignments: dict[str, CSPAssignment] = {}
        used_ambulances: set[str] = set()
        remaining_beds = {
            h.id: h.available_beds for h in state.hospitals.values()
        }

        solved = self._search(
            state,
            domains,
            assignments,
            used_ambulances,
            remaining_beds,
            stats,
            trace,
        )

        if solved:
            status = "SOLVED"
            unassigned = {}
        else:
            # Return a useful partial result rather than pretending a complete
            # allocation exists when the constraints are genuinely unsatisfied.
            status = "PARTIAL" if assignments else "UNSATISFIABLE"
            for emergency in emergencies:
                if emergency.id not in assignments:
                    if not original_domains[emergency.id]:
                        unassigned.setdefault(emergency.id, "NO_VALID_ASSIGNMENT")
                    else:
                        unassigned.setdefault(emergency.id, "CONFLICT_WITH_EXISTING_ASSIGNMENTS")

        return CSPResult(
            status=status,
            assignments=assignments,
            unassigned=unassigned,
            constraints_checked=stats.constraints_checked,
            conflicts=stats.conflicts,
            backtracks=stats.backtracks,
            domain_reductions=stats.domain_reductions,
            execution_ms=round((perf_counter() - started) * 1000, 4),
            trace=trace,
        )

    def apply(self, state: WorldState, result: CSPResult) -> CSPResult:
        """Commit a solved/partial allocation to the live simulation state."""
        if not result.assignments:
            return result

        for emergency_id, assignment in result.assignments.items():
            emergency = state.emergencies.get(emergency_id)
            ambulance = state.ambulances.get(assignment.ambulance_id)
            hospital = state.hospitals.get(assignment.hospital_id)
            if emergency is None or ambulance is None or hospital is None:
                continue
            emergency.assigned_ambulance = ambulance.id
            emergency.assigned_hospital = hospital.id
            emergency.status = EmergencyStatus.ALLOCATED
            ambulance.assigned_emergency = emergency.id
            ambulance.status = AmbulanceStatus.DISPATCHED
            hospital.available_beds = max(0, hospital.available_beds - emergency.patients)
        return result

    def _build_domain(
        self,
        state: WorldState,
        emergency,
        avoid: frozenset[str],
        stats: SolveStats,
        trace: list[CSPTraceStep],
    ) -> list[Candidate]:
        candidates: list[Candidate] = []
        for ambulance in sorted(state.ambulances.values(), key=lambda a: a.id):
            stats.constraints_checked += 1
            if ambulance.status is not AmbulanceStatus.AVAILABLE:
                self._trace(trace, stats, emergency.id, ambulance.id, "REJECT", "ambulance_not_available")
                continue
            if ambulance.capacity < emergency.patients:
                self._trace(trace, stats, emergency.id, ambulance.id, "REJECT", "insufficient_ambulance_capacity")
                continue

            to_scene = routing_service.route(
                state, ambulance.node_id, emergency.node_id, avoid=avoid, use_cache=True
            )
            stats.constraints_checked += 1
            if not to_scene.found:
                self._trace(trace, stats, emergency.id, ambulance.id, "REJECT", "no_safe_route_to_emergency")
                continue

            for hospital in sorted(state.hospitals.values(), key=lambda h: h.id):
                stats.constraints_checked += 1
                if hospital.status is HospitalStatus.FULL:
                    self._trace(trace, stats, emergency.id, f"{ambulance.id}->{hospital.id}", "REJECT", "hospital_full")
                    continue
                if hospital.available_beds < emergency.patients:
                    self._trace(trace, stats, emergency.id, f"{ambulance.id}->{hospital.id}", "REJECT", "insufficient_hospital_beds")
                    continue
                to_hospital = routing_service.route(
                    state, emergency.node_id, hospital.node_id, avoid=avoid, use_cache=True
                )
                stats.constraints_checked += 1
                if not to_hospital.found:
                    self._trace(trace, stats, emergency.id, f"{ambulance.id}->{hospital.id}", "REJECT", "no_safe_route_to_hospital")
                    continue
                candidates.append(
                    Candidate(
                        ambulance_id=ambulance.id,
                        hospital_id=hospital.id,
                        route_to_scene_cost=to_scene.total_cost,
                        route_to_hospital_cost=to_hospital.total_cost,
                    )
                )

        candidates.sort(
            key=lambda c: (
                c.route_to_scene_cost + c.route_to_hospital_cost,
                c.ambulance_id,
                c.hospital_id,
            )
        )
        return candidates

    def _search(
        self,
        state: WorldState,
        domains: dict[str, list[Candidate]],
        assignments: dict[str, CSPAssignment],
        used_ambulances: set[str],
        remaining_beds: dict[str, int],
        stats: SolveStats,
        trace: list[CSPTraceStep],
    ) -> bool:
        if len(assignments) == len(domains):
            return True

        # MRV: select the unassigned variable with the smallest current domain.
        unassigned_ids = [key for key in domains if key not in assignments]
        variable = min(
            unassigned_ids,
            key=lambda eid: (len(domains[eid]), eid),
        )
        current_domain = list(domains[variable])
        if not current_domain:
            stats.conflicts += 1
            return False

        for candidate in current_domain:
            stats.step += 1
            label = f"{candidate.ambulance_id}->{candidate.hospital_id}"
            if candidate.ambulance_id in used_ambulances:
                stats.constraints_checked += 1
                stats.conflicts += 1
                self._trace(trace, stats, variable, label, "REJECT", "ambulance_already_assigned")
                continue
            # Hospital capacity is consumed by the emergency's patient count.
            emergency = state.emergencies[variable]
            if remaining_beds[candidate.hospital_id] < emergency.patients:
                stats.constraints_checked += 1
                stats.conflicts += 1
                self._trace(trace, stats, variable, label, "REJECT", "hospital_capacity_conflict")
                continue

            assignments[variable] = CSPAssignment(
                ambulance_id=candidate.ambulance_id,
                hospital_id=candidate.hospital_id,
            )
            used_ambulances.add(candidate.ambulance_id)
            remaining_beds[candidate.hospital_id] -= emergency.patients
            self._trace(trace, stats, variable, label, "ASSIGN", "all_local_constraints_satisfied")

            # Forward checking: prune values that are now impossible because
            # the ambulance is consumed or the hospital no longer has capacity.
            reductions: list[tuple[str, list[Candidate]]] = []
            failed = False
            for other in unassigned_ids:
                if other == variable:
                    continue
                before = domains[other]
                after = [
                    value
                    for value in before
                    if value.ambulance_id not in used_ambulances
                    and remaining_beds[value.hospital_id] >= state.emergencies[other].patients
                ]
                if len(after) != len(before):
                    stats.domain_reductions += len(before) - len(after)
                    reductions.append((other, before))
                    domains[other] = after
                    self._trace(
                        trace,
                        stats,
                        other,
                        "*",
                        "PRUNE",
                        f"forward_check_removed_{len(before) - len(after)}_values",
                    )
                if not after:
                    failed = True
                    stats.conflicts += 1
                    break

            if not failed and self._search(
                state,
                domains,
                assignments,
                used_ambulances,
                remaining_beds,
                stats,
                trace,
            ):
                return True

            for other, before in reductions:
                domains[other] = before
            remaining_beds[candidate.hospital_id] += emergency.patients
            used_ambulances.remove(candidate.ambulance_id)
            del assignments[variable]
            stats.backtracks += 1
            self._trace(trace, stats, variable, label, "BACKTRACK", "candidate_led_to_downstream_conflict")

        return False

    @staticmethod
    def _trace(
        trace: list[CSPTraceStep],
        stats: SolveStats,
        variable: str,
        value: str,
        outcome: str,
        reason: str,
    ) -> None:
        trace.append(
            CSPTraceStep(
                step=stats.step,
                variable=variable,
                value=value,
                outcome=outcome,
                reason=reason,
            )
        )


csp_allocator = CSPAllocator()
