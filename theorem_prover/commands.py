"""
PA axiom commands and inference rules.

Each function validates its inputs, constructs the resulting Prop, appends it
to the session fact_list, and returns it.  Commands are the only way facts
enter the list.

fact_list is module-level state.  Call reset_session() to clear it.
"""
from __future__ import annotations
from .types import Zero, Succ, Add, Eq, Neq, Not, Imp, Num, Term, Prop
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
# Rewrite: term-substitution engine
# ---------------------------------------------------------------------------

def _count_in_term(term: Term, find: Term) -> int:
    """Count how many times `find` appears as a subterm of `term`."""
    if term == find:
        return 1  # match at this node; don't recurse into its children
    if isinstance(term, Succ):
        return _count_in_term(term.pred, find)
    if isinstance(term, Add):
        return _count_in_term(term.left, find) + _count_in_term(term.right, find)
    return 0


def _count_in_prop(prop: Prop, find: Term) -> int:
    """Count how many times `find` appears in the terms of `prop`."""
    if isinstance(prop, (Eq, Neq)):
        return _count_in_term(prop.left, find) + _count_in_term(prop.right, find)
    if isinstance(prop, Not):
        return _count_in_prop(prop.prop, find)
    if isinstance(prop, Imp):
        return _count_in_prop(prop.antecedent, find) + _count_in_prop(prop.consequent, find)
    return 0


def _subst_one_in_term(term: Term, find: Term, replace: Term, pos: int) -> tuple:
    """
    Substitute the `pos`-th (0-indexed) occurrence of `find` with `replace`.
    Returns (new_term, remaining) where remaining decrements per occurrence;
    remaining == -1 signals that the substitution has been performed.
    """
    if term == find:
        if pos == 0:
            return replace, -1  # done
        return term, pos - 1

    if isinstance(term, Succ):
        new_pred, remaining = _subst_one_in_term(term.pred, find, replace, pos)
        return Succ(new_pred), remaining

    if isinstance(term, Add):
        new_left, remaining = _subst_one_in_term(term.left, find, replace, pos)
        if remaining == -1:
            return Add(new_left, term.right), -1  # short-circuit
        new_right, remaining = _subst_one_in_term(term.right, find, replace, remaining)
        return Add(new_left, new_right), remaining

    return term, pos


def _subst_one_in_prop(prop: Prop, find: Term, replace: Term, pos: int) -> tuple:
    """
    Substitute the `pos`-th occurrence of `find` in the terms of `prop`.
    Returns (new_prop, remaining); remaining == -1 means substitution done.
    """
    if isinstance(prop, (Eq, Neq)):
        cls = type(prop)
        new_left, remaining = _subst_one_in_term(prop.left, find, replace, pos)
        if remaining == -1:
            return cls(new_left, prop.right), -1
        new_right, remaining = _subst_one_in_term(prop.right, find, replace, remaining)
        return cls(new_left, new_right), remaining

    if isinstance(prop, Not):
        new_inner, remaining = _subst_one_in_prop(prop.prop, find, replace, pos)
        return Not(new_inner), remaining

    if isinstance(prop, Imp):
        new_ant, remaining = _subst_one_in_prop(prop.antecedent, find, replace, pos)
        if remaining == -1:
            return Imp(new_ant, prop.consequent), -1
        new_con, remaining = _subst_one_in_prop(prop.consequent, find, replace, remaining)
        return Imp(new_ant, new_con), remaining

    return prop, pos


def rewrite_options(eq: Eq, target: Prop) -> list:
    """
    Return all unique Props obtainable from `target` by replacing exactly one
    occurrence of `eq.left` with `eq.right`, or one occurrence of `eq.right`
    with `eq.left`.  Does not record anything.
    """
    results: list[Prop] = []
    seen: set[Prop] = set()
    for find, replace in [(eq.left, eq.right), (eq.right, eq.left)]:
        for pos in range(_count_in_prop(target, find)):
            new_prop, _ = _subst_one_in_prop(target, find, replace, pos)
            if new_prop != target and new_prop not in seen:
                seen.add(new_prop)
                results.append(new_prop)
    return results


def record_prop(prop: Prop) -> Prop:
    """Record an already-validated Prop into the session fact list."""
    return _record(prop)


def rewrite(eq_arg, target_arg) -> Prop:
    """
    Rewrite `target_arg` using the equality `eq_arg`.
    Auto-applies if exactly one substitution is possible; raises otherwise.
    """
    check_valid_prop(eq_arg)
    check_valid_prop(target_arg)
    if not isinstance(eq_arg, Eq):
        raise InvalidInput(
            f"rewrite() first argument must be an Eq, got {type(eq_arg).__name__}"
        )
    options = rewrite_options(eq_arg, target_arg)
    if len(options) == 0:
        raise InvalidInput("No rewrites possible")
    if len(options) == 1:
        return _record(options[0])
    raise InvalidInput(
        f"{len(options)} rewrites possible — use the interactive rewrite picker "
        f"(shift-click two facts in the web UI)"
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
    "rewrite":       (rewrite,       2),
}
