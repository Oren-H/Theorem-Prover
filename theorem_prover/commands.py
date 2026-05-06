"""
PA axiom commands and inference rules.

Each function validates its inputs, constructs the resulting Prop, appends it
to the session fact_list, and returns it.  Commands are the only way facts
enter the list.

fact_list is module-level state.  Call reset_session() to clear it.
"""
from __future__ import annotations
from .types import Zero, Succ, Add, Eq, Neq, Not, Imp, ForAll, Var, Num, Term, Prop
from .validation import check_valid_num, check_valid_term, check_valid_prop
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
# Variable substitution helpers
# ---------------------------------------------------------------------------

def subst_term(term: Term, var: str, replacement: Term) -> Term:
    """Replace every occurrence of Var(var) in term with replacement."""
    if isinstance(term, Var):
        return replacement if term.name == var else term
    if isinstance(term, Zero):
        return term
    if isinstance(term, Succ):
        return Succ(subst_term(term.pred, var, replacement))
    if isinstance(term, Add):
        return Add(
            subst_term(term.left, var, replacement),
            subst_term(term.right, var, replacement),
        )
    return term


def subst_prop(prop: Prop, var: str, replacement: Term) -> Prop:
    """Replace every occurrence of Var(var) in the terms of prop with replacement."""
    if isinstance(prop, (Eq, Neq)):
        cls = type(prop)
        return cls(
            subst_term(prop.left, var, replacement),
            subst_term(prop.right, var, replacement),
        )
    if isinstance(prop, Not):
        return Not(subst_prop(prop.prop, var, replacement))
    if isinstance(prop, Imp):
        return Imp(
            subst_prop(prop.antecedent, var, replacement),
            subst_prop(prop.consequent, var, replacement),
        )
    if isinstance(prop, ForAll):
        if prop.var == var:  # bound variable shadows the substitution
            return prop
        return ForAll(prop.var, subst_prop(prop.body, var, replacement))
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
# Term and Prop constructors
# ---------------------------------------------------------------------------

def mk_add(t1, t2) -> Add:
    """Construct Add(t1, t2) as a term. Does not record to fact_list."""
    check_valid_term(t1)
    check_valid_term(t2)
    return Add(t1, t2)


def mk_eq(t1, t2) -> Eq:
    """Assert t1 = t2 as a hypothesis and record it."""
    check_valid_term(t1)
    check_valid_term(t2)
    return _record(Eq(t1, t2))


# ---------------------------------------------------------------------------
# Induction inference rules
# ---------------------------------------------------------------------------

def imp_intro(P, Q) -> Imp:
    """Given Props P and Q, record the implication P ⇒ Q."""
    check_valid_prop(P)
    check_valid_prop(Q)
    return _record(Imp(P, Q))


def forall_intro(n, P) -> ForAll:
    """Given Var n and Prop P, record ∀n. P."""
    if not isinstance(n, Var):
        raise InvalidInput(
            f"forall_intro() first argument must be a variable (e.g. n), "
            f"got {type(n).__name__}"
        )
    check_valid_prop(P)
    return _record(ForAll(n.name, P))


def induction(base, step) -> ForAll:
    """
    PA induction schema.

    base : Prop              — must equal P[var := 0]
    step : ForAll(var, P⇒Q) — must have Q == P[var := var++]

    Derives ∀var. P.
    """
    check_valid_prop(base)
    check_valid_prop(step)
    if not isinstance(step, ForAll):
        raise InvalidInput(
            f"induction() second argument must be ∀n.(P ⇒ Q), "
            f"got {type(step).__name__}"
        )
    if not isinstance(step.body, Imp):
        raise InvalidInput(
            f"induction() step body must be an implication (P ⇒ Q), "
            f"got {type(step.body).__name__}"
        )
    var = step.var
    P = step.body.antecedent
    Q = step.body.consequent

    expected_Q = subst_prop(P, var, Succ(Var(var)))
    if Q != expected_Q:
        from .display import display_prop
        raise InvalidInput(
            f"induction() step consequent must be P[{var}:={var}++].\n"
            f"  Expected: {display_prop(expected_Q)}\n"
            f"  Got:      {display_prop(Q)}"
        )

    expected_base = subst_prop(P, var, Zero())
    if base != expected_base:
        from .display import display_prop
        raise InvalidInput(
            f"induction() base case must be P[{var}:=0].\n"
            f"  Expected: {display_prop(expected_base)}\n"
            f"  Got:      {display_prop(base)}"
        )

    return _record(ForAll(var, P))


def inst(fa, t) -> Prop:
    """Instantiate ∀var. P at term t, deriving P[var := t]."""
    check_valid_prop(fa)
    check_valid_term(t)
    if not isinstance(fa, ForAll):
        raise InvalidInput(
            f"inst() first argument must be a ∀-proposition, "
            f"got {type(fa).__name__}"
        )
    return _record(subst_prop(fa.body, fa.var, t))


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


def rewrite_fwd(eq_arg, target_arg) -> Prop:
    """
    Rewrite `target_arg` using the equality `eq_arg`, forward direction only
    (replaces eq.left with eq.right). Useful when reverse rewrites are ambiguous.
    Auto-applies if exactly one forward substitution is possible; raises otherwise.
    """
    check_valid_prop(eq_arg)
    check_valid_prop(target_arg)
    if not isinstance(eq_arg, Eq):
        raise InvalidInput(
            f"rewrite_fwd() first argument must be an Eq, got {type(eq_arg).__name__}"
        )
    options: list[Prop] = []
    seen: set[Prop] = set()
    n = _count_in_prop(target_arg, eq_arg.left)
    for pos in range(n):
        new_prop, _ = _subst_one_in_prop(target_arg, eq_arg.left, eq_arg.right, pos)
        if new_prop != target_arg and new_prop not in seen:
            seen.add(new_prop)
            options.append(new_prop)
    if len(options) == 0:
        raise InvalidInput("No forward rewrites possible")
    if len(options) == 1:
        return _record(options[0])
    raise InvalidInput(
        f"{len(options)} forward rewrites possible — be more specific"
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
    "rewrite_fwd":   (rewrite_fwd,   2),
    "mk_add":        (mk_add,        2),
    "mk_eq":         (mk_eq,         2),
    "imp_intro":     (imp_intro,     2),
    "forall_intro":  (forall_intro,  2),
    "induction":     (induction,     2),
    "inst":          (inst,          2),
}
