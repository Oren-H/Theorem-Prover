"""
Validation predicates for the PA type system.

check_valid_num  — accepts Zero or Succ, rejects everything else.
check_valid_term — accepts Num or Add (with Term children), rejects Props.
check_valid_prop — accepts Eq, Neq, Not, Imp with correctly-typed children.
"""
from __future__ import annotations
from .types import Zero, Succ, Add, Eq, Neq, Not, Imp
from .errors import InvalidInput


def check_valid_num(x) -> bool:
    """Return True if x is a valid Num; raise InvalidInput otherwise."""
    if isinstance(x, Zero):
        return True
    if isinstance(x, Succ):
        return check_valid_num(x.pred)
    raise InvalidInput(
        f"Expected a Num (Zero or Succ), got {type(x).__name__}: {x!r}"
    )


def check_valid_term(x) -> bool:
    """Return True if x is a valid Term; raise InvalidInput if it is a Prop."""
    if isinstance(x, (Zero, Succ)):
        return check_valid_num(x)
    if isinstance(x, Add):
        check_valid_term(x.left)
        check_valid_term(x.right)
        return True
    if isinstance(x, (Eq, Neq, Not, Imp)):
        raise InvalidInput(
            f"Expected a Term (Num or Add), got Prop {type(x).__name__}: {x!r}"
        )
    raise InvalidInput(
        f"Expected a Term, got {type(x).__name__}: {x!r}"
    )


def check_valid_prop(x) -> bool:
    """Return True if x is a valid Prop; raise InvalidInput otherwise."""
    if isinstance(x, (Eq, Neq)):
        check_valid_term(x.left)
        check_valid_term(x.right)
        return True
    if isinstance(x, Not):
        check_valid_prop(x.prop)
        return True
    if isinstance(x, Imp):
        check_valid_prop(x.antecedent)
        check_valid_prop(x.consequent)
        return True
    if isinstance(x, (Zero, Succ, Add)):
        raise InvalidInput(
            f"Expected a Prop, got Term {type(x).__name__}: {x!r}"
        )
    raise InvalidInput(
        f"Expected a Prop, got {type(x).__name__}: {x!r}"
    )
