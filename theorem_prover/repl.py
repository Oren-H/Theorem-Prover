"""
Simple terminal REPL for the PA Theorem Prover.

Run this module directly for a plain-text interactive session:
    python -m theorem_prover.repl

Features
--------
- Accepts command strings as defined in the spec.
- Prints the resulting prop and the updated fact list after each command.
- Graceful error display (no crash on invalid input).
- Built-in commands: help, list, reset, quit / exit.
"""
from __future__ import annotations
import sys

from .commands import fact_list, reset_session
from .display import display_prop
from .parser import parse_and_run
from .errors import InvalidCommand, InvalidInput, TypeMismatch

try:
    import readline  # noqa: F401 — enables arrow-key history on Unix
except ImportError:
    pass


HELP_TEXT = """\
PA Theorem Prover — interactive REPL
=====================================
Axiom commands
  succ_not_zero(n)      n++ ≠ 0
  succ_imp_eq(n, m)     n++ = m++ ⇒ n = m
  add_zero_eq(n)        n + 0 = n
  add_succ_eq(n, m)     n + m++ = (n+m)++

Inference rules
  cont(L)               contrapositive of implication L
  mp(P, L)              modus ponens: P, P⇒Q ⊢ Q
  flip(P)               symmetry of equality / inequality

Input notation
  0, 1, 2, …            integer literals → Num
  0++, (0++)++, …       successor notation → Num
  #N                    reference fact N from the fact list

Built-in commands
  help                  show this message
  list                  print the current fact list
  reset                 clear the session
  quit / exit           end the session
"""


def _print_fact_list() -> None:
    if not fact_list:
        print("  (no facts yet)")
        return
    width = len(str(len(fact_list)))
    for i, prop in enumerate(fact_list, 1):
        print(f"  #{i:<{width}}  {display_prop(prop)}")


def run_repl() -> None:
    print("PA Theorem Prover  |  type 'help' for commands, 'quit' to exit")
    print()

    while True:
        try:
            raw = input("⊢ ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        if raw.lower() in ("quit", "exit"):
            break
        if raw.lower() == "help":
            print(HELP_TEXT)
            continue
        if raw.lower() == "list":
            _print_fact_list()
            continue
        if raw.lower() == "reset":
            reset_session()
            print("Session reset.")
            continue

        try:
            result = parse_and_run(raw)
        except InvalidCommand as e:
            print(f"[error: unknown command]  {e}")
            continue
        except InvalidInput as e:
            print(f"[error: invalid input]  {e}")
            continue
        except TypeMismatch as e:
            print(f"[error: type mismatch]  {e}")
            continue
        except Exception as e:
            print(f"[error]  {e}")
            continue

        from .types import Zero, Succ, Add, Prop
        if isinstance(result, (Zero, Succ, Add)):
            from .display import display_term
            print(f"  = {display_term(result)}")
        else:
            print(f"  ✓  {display_prop(result)}")
        print()
        _print_fact_list()
        print()


if __name__ == "__main__":
    run_repl()
