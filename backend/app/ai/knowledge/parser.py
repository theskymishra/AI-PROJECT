"""Small, deterministic parser for the positive Horn-clause subset used here.

The project only needs a teachable subset of FOL: predicates, constants,
variables and conjunctions. Negation and function symbols are deliberately not
implemented because the forward-chaining engine is intended to remain easy to
inspect during a viva.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_IDENTIFIER = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)$")
_ATOM = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$")


@dataclass(frozen=True, slots=True)
class Atom:
    predicate: str
    args: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.predicate):
            raise ValueError(f"invalid predicate {self.predicate!r}")
        if not self.args:
            raise ValueError("an atom must contain at least one argument")
        if any(not _IDENTIFIER.fullmatch(a) for a in self.args):
            raise ValueError(f"invalid atom arguments: {self.args!r}")

    def __str__(self) -> str:
        return format_atom(self)


def _split_args(raw: str) -> tuple[str, ...]:
    args = tuple(part.strip() for part in raw.split(","))
    if not args or any(not a for a in args):
        raise ValueError(f"invalid argument list {raw!r}")
    return args


def parse_atom(text: str) -> Atom:
    """Parse ``Predicate(A,B)`` into an Atom."""
    value = text.strip()
    match = _ATOM.fullmatch(value)
    if not match:
        raise ValueError(f"invalid atom {text!r}; expected Predicate(A,B)")
    return Atom(match.group(1), _split_args(match.group(2)))


def parse_conjunction(text: str) -> tuple[Atom, ...]:
    """Parse ``A(x) & B(x)`` into atoms."""
    atoms = tuple(parse_atom(part) for part in text.split("&"))
    if not atoms:
        raise ValueError("empty conjunction")
    return atoms


def parse_rule(text: str) -> tuple[tuple[Atom, ...], Atom]:
    """Parse ``A(x) & B(x) -> C(x)``."""
    parts = text.split("->")
    if len(parts) != 2:
        raise ValueError("a rule must contain exactly one '->'")
    premises = parse_conjunction(parts[0])
    conclusion = parse_atom(parts[1])
    return premises, conclusion


def is_variable(term: str) -> bool:
    """Variables conventionally start with an uppercase letter."""
    return bool(re.fullmatch(r"[A-Z]", term))


def format_atom(atom: Atom) -> str:
    return f"{atom.predicate}({', '.join(atom.args)})"
