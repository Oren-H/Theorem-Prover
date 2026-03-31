"""
Recursive display renderer for Props and Terms.

Uses Unicode: ≠ for inequality, ⇒ for implication, ¬ for negation.
Parentheses are added when needed for unambiguous reading.
"""
from __future__ import annotations
from .types import Zero, Succ, Add, Eq, Neq, Not, Imp


def display_term(t) -> str:
    """Render a Term as a human-readable string."""
    if isinstance(t, Zero):
        return "0"
    if isinstance(t, Succ):
        inner = display_term(t.pred)
        # Wrap in parens when inner is a Succ or Add to keep ++ binding clear.
        if isinstance(t.pred, (Succ, Add)):
            return f"({inner})++"
        return f"{inner}++"
    if isinstance(t, Add):
        left = display_term(t.left)
        right = display_term(t.right)
        # Parenthesise the left child if it is itself an Add (left-assoc).
        if isinstance(t.left, Add):
            left = f"({left})"
        return f"{left} + {right}"
    return repr(t)


def display_prop(p) -> str:
    """Render a Prop as a human-readable string."""
    if isinstance(p, Eq):
        return f"{display_term(p.left)} = {display_term(p.right)}"
    if isinstance(p, Neq):
        return f"{display_term(p.left)} \u2260 {display_term(p.right)}"
    if isinstance(p, Not):
        # Not(Eq(...)) renders as ≠ for readability.
        if isinstance(p.prop, Eq):
            return (
                f"{display_term(p.prop.left)} \u2260 {display_term(p.prop.right)}"
            )
        # Not(Neq(...)) renders as =.
        if isinstance(p.prop, Neq):
            return (
                f"{display_term(p.prop.left)} = {display_term(p.prop.right)}"
            )
        inner = display_prop(p.prop)
        return f"\u00ac({inner})"
    if isinstance(p, Imp):
        left = display_prop(p.antecedent)
        right = display_prop(p.consequent)
        # Parenthesise sub-implications to clarify nesting.
        if isinstance(p.antecedent, Imp):
            left = f"({left})"
        if isinstance(p.consequent, Imp):
            right = f"({right})"
        return f"{left} \u21d2 {right}"
    return repr(p)
