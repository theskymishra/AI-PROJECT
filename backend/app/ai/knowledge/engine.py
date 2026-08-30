"""Forward chaining and conjunctive first-order queries.

This is intentionally a small positive Horn-clause engine. It implements the
part of symbolic AI the project needs to demonstrate: facts, variables,
unification, rule firing, fixpoint iteration and explainable inference steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable

from app.ai.knowledge.parser import Atom, format_atom, is_variable
from app.models.ai_result import FOLResult, InferenceResult, InferenceStep


Fact = Atom


@dataclass(frozen=True, slots=True)
class Rule:
    name: str
    premises: tuple[Atom, ...]
    conclusion: Atom


Substitution = dict[str, str]


class KnowledgeEngine:
    """A deterministic forward-chaining knowledge base."""

    def __init__(self, facts: Iterable[Fact] = (), rules: Iterable[Rule] = ()) -> None:
        self.facts: set[Fact] = set(facts)
        self.rules: tuple[Rule, ...] = tuple(rules)

    def add_fact(self, fact: Fact) -> None:
        self.facts.add(fact)

    def add_rule(self, rule: Rule) -> None:
        self.rules = (*self.rules, rule)

    def infer(self) -> InferenceResult:
        """Apply rules until no new facts can be produced."""
        started = perf_counter()
        initial = set(self.facts)
        derived: list[Fact] = []
        steps: list[InferenceStep] = []
        iterations = 0

        while True:
            iterations += 1
            additions: list[tuple[Fact, Rule, Substitution, tuple[Fact, ...]]] = []
            known = set(self.facts)

            for rule in self.rules:
                for bindings, matched in self._match_rule(rule, known):
                    conclusion = substitute(rule.conclusion, bindings)
                    if conclusion in known or any(c == conclusion for c, *_ in additions):
                        continue
                    additions.append((conclusion, rule, bindings, matched))

            if not additions:
                break

            for conclusion, rule, bindings, matched in additions:
                self.facts.add(conclusion)
                derived.append(conclusion)
                steps.append(
                    InferenceStep(
                        rule_name=rule.name,
                        bindings=dict(sorted(bindings.items())),
                        premises=[format_atom(a) for a in matched],
                        conclusion=format_atom(conclusion),
                    )
                )

        return InferenceResult(
            initial_facts=sorted(format_atom(f) for f in initial),
            derived_facts=sorted(format_atom(f) for f in derived),
            steps=steps,
            iterations=iterations,
            execution_ms=round((perf_counter() - started) * 1000, 4),
        )

    def query(self, patterns: Iterable[Atom], *, execute_inference: bool = True) -> FOLResult:
        """Evaluate a positive conjunctive FOL query against the KB."""
        started = perf_counter()
        if execute_inference:
            self.infer()
        patterns = tuple(patterns)
        if not patterns:
            raise ValueError("query must contain at least one atom")

        bindings_list: list[Substitution] = []
        for binding in _match_conjunction(patterns, self.facts):
            bindings_list.append(binding)

        # Only expose variables occurring in the query. Sorting makes the wire
        # result deterministic across Python hash-table/set ordering.
        variables = sorted({term for atom in patterns for term in atom.args if is_variable(term)})
        visible = [
            {var: binding[var] for var in variables if var in binding}
            for binding in bindings_list
        ]
        visible.sort(key=lambda row: tuple(row.get(v, "") for v in variables))

        return FOLResult(
            query=" & ".join(format_atom(a) for a in patterns),
            bindings=visible,
            count=len(visible),
            execution_ms=round((perf_counter() - started) * 1000, 4),
        )

    @staticmethod
    def _match_rule(rule: Rule, facts: set[Fact]):
        for binding, matched in _match_conjunction_with_matches(rule.premises, facts):
            yield binding, matched


def substitute(atom: Atom, bindings: Substitution) -> Atom:
    return Atom(atom.predicate, tuple(bindings.get(arg, arg) for arg in atom.args))


def _unify(pattern: Atom, fact: Fact, existing: Substitution) -> Substitution | None:
    if pattern.predicate != fact.predicate or len(pattern.args) != len(fact.args):
        return None
    result = dict(existing)
    for pattern_arg, fact_arg in zip(pattern.args, fact.args):
        if is_variable(pattern_arg):
            previous = result.get(pattern_arg)
            if previous is not None and previous != fact_arg:
                return None
            result[pattern_arg] = fact_arg
        elif pattern_arg != fact_arg:
            return None
    return result


def _match_conjunction_with_matches(
    patterns: tuple[Atom, ...], facts: set[Fact]
):
    def visit(index: int, bindings: Substitution, matched: tuple[Fact, ...]):
        if index == len(patterns):
            yield bindings, matched
            return
        pattern = substitute(patterns[index], bindings)
        candidates = sorted(
            facts,
            key=lambda f: (f.predicate, f.args),
        )
        for fact in candidates:
            merged = _unify(pattern, fact, bindings)
            if merged is not None:
                yield from visit(index + 1, merged, matched + (fact,))

    yield from visit(0, {}, ())


def _match_conjunction(patterns: tuple[Atom, ...], facts: set[Fact]):
    yield from (binding for binding, _ in _match_conjunction_with_matches(patterns, facts))
