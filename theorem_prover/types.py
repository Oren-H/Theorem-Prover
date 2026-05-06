"""
Core type system for Peano Arithmetic.

Strictly separates Terms (Num, Add) from Props (Eq, Neq, Not, Imp).
All types are frozen dataclasses — structural equality and hashing come for free.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Union


# ---------------------------------------------------------------------------
# Numeric terms
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Zero:
    """The constant 0."""


@dataclass(frozen=True)
class Succ:
    """Successor: wraps another Num."""
    pred: "Num"


@dataclass(frozen=True)
class Var:
    """A natural number variable, e.g. Var('n') represents n."""
    name: str


Num = Union[Zero, Succ, Var]


@dataclass(frozen=True)
class Add:
    """Addition: pair of Terms."""
    left: "Term"
    right: "Term"


Term = Union[Num, Add]   # Props are NEVER Terms


# ---------------------------------------------------------------------------
# Propositions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Eq:
    """Equality of two Terms: left = right."""
    left: Term
    right: Term


@dataclass(frozen=True)
class Neq:
    """Syntactic sugar for Not(Eq(left, right)): left ≠ right."""
    left: Term
    right: Term


@dataclass(frozen=True)
class Not:
    """Negation of a Prop."""
    prop: "Prop"


@dataclass(frozen=True)
class Imp:
    """Implication: antecedent ⇒ consequent."""
    antecedent: "Prop"
    consequent: "Prop"


@dataclass(frozen=True)
class ForAll:
    """Universal quantification: ∀var. body"""
    var: str
    body: "Prop"


Prop = Union[Eq, Neq, Not, Imp, ForAll]
