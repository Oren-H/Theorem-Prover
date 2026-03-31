"""
PA axiom commands and inference rules.

Each function validates its inputs, constructs the resulting Prop, appends it
to the session fact_list, and returns it.  Commands are the only way facts
enter the list.

fact_list is module-level state.  Call reset_session() to clear it.
"""
from __future__ import annotations
from .types import Zero, Succ, Add, Eq, Neq, Not, Imp, Num, Prop
from .validation import check_valid_num, check_valid_prop
from .errors import InvalidInput, TypeMismatch

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

fact_list: list[Prop] = []


def reset_session() -> None:
    fact_list.clear()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _int_to_num(n: int) -> Num:
    if n < 0:
        raise InvalidInput(f"Expected a non-negative integer, got {n}")
    result: Num = Zero()
    for _ in range(n):
        result = Succ(result)
    return result


def _make_num(x) -> Num:
    """Accept a Python int or a Num; always return a Num."""
    if isinstance(x, int):
        return _int_to_num(x)
    check_valid_num(x)
    return x


def _props_equal(a: Prop, b: Prop) -> bool:
    """
    Structural equality that identifies Neq(x,y) with Not(Eq(x,y)).
    Used by mp() to match an implication's antecedent against the supplied Prop.
    """
    if a == b:
        return True
    # Neq(x,y) ≡ Not(Eq(x,y))
    if isinstance(a, Neq) and isinstance(b, Not) and isinstance(b.prop, Eq):
        return a.left == b.prop.left and a.right == b.prop.right
    if isinstance(b, Neq) and isinstance(a, Not) and isinstance(a.prop, Eq):
        return b.left == a.prop.left and b.right == a.prop.right
    return False


def _record(prop: Prop) -> Prop:
    fact_list.append(prop)
    return prop


# ---------------------------------------------------------------------------
# Peano axioms
# ---------------------------------------------------------------------------

def succ_not_zero(n) -> Neq:
    """Peano axiom: n++ ≠ 0"""
    n = _make_num(n)
    return _record(Neq(Succ(n), Zero()))


def succ_imp_eq(n, m) -> Imp:
    """Peano axiom: n++ = m++ ⇒ n = m  (successor is injective)"""
    n = _make_num(n)
    m = _make_num(m)
    return _record(Imp(Eq(Succ(n), Succ(m)), Eq(n, m)))


def add_zero_eq(n) -> Eq:
    """Peano axiom: n + 0 = n  (adding zero is identity)"""
    n = _make_num(n)
    return _record(Eq(Add(n, Zero()), n))


def add_succ_eq(n, m) -> Eq:
    """Peano axiom: n + m++ = (n + m)++  (addition of successor)"""
    n = _make_num(n)
    m = _make_num(m)
    return _record(Eq(Add(n, Succ(m)), Succ(Add(n, m))))


# ---------------------------------------------------------------------------
# Inference rules
# ---------------------------------------------------------------------------

def cont(L) -> Imp:
    """Contrapositive: given P ⇒ Q, produce ¬Q ⇒ ¬P."""
    check_valid_prop(L)
    if not isinstance(L, Imp):
        raise InvalidInput(
            f"cont() expects an implication (P ⇒ Q), got {type(L).__name__}"
        )
    return _record(Imp(Not(L.consequent), Not(L.antecedent)))


def mp(P, L) -> Prop:
    """Modus ponens: given P and P ⇒ Q, derive Q."""
    check_valid_prop(P)
    check_valid_prop(L)
    if not isinstance(L, Imp):
        raise InvalidInput(
            f"mp() second argument must be an implication (P ⇒ Q), "
            f"got {type(L).__name__}"
        )
    if not _props_equal(L.antecedent, P):
        from .display import display_prop
        raise TypeMismatch(
            f"Antecedent of implication is  {display_prop(L.antecedent)}\n"
            f"but supplied prop is           {display_prop(P)}"
        )
    return _record(L.consequent)


# ---------------------------------------------------------------------------
# Placeholder — Induction schema (reserved for a future version)
# ---------------------------------------------------------------------------
# def induction(base, step):
#     """PA induction schema — not yet implemented (out of scope for v0.1)."""
#     raise NotImplementedError("Induction is not yet implemented")


def flip(P) -> Prop:
    """Symmetry of equality: p = r  ↦  r = p  (also works on Neq)."""
    check_valid_prop(P)
    if isinstance(P, Eq):
        return _record(Eq(P.right, P.left))
    if isinstance(P, Neq):
        return _record(Neq(P.right, P.left))
    raise InvalidInput(
        f"flip() expects an Eq or Neq prop, got {type(P).__name__}"
    )


# ---------------------------------------------------------------------------
# Command registry (used by the parser/dispatcher)
# ---------------------------------------------------------------------------

COMMANDS: dict[str, tuple] = {
    "succ_not_zero": (succ_not_zero, 1),
    "succ_imp_eq":   (succ_imp_eq,   2),
    "add_zero_eq":   (add_zero_eq,   1),
    "add_succ_eq":   (add_succ_eq,   2),
    "cont":          (cont,          1),
    "mp":            (mp,            2),
    "flip":          (flip,          1),
}
