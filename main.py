"""
Entry point for the PA Theorem Prover.

Usage
-----
    python main.py           # launch the Textual TUI (default)
    python main.py --repl    # plain terminal REPL (no TUI dependency)
    python main.py --test    # run the built-in spec proof examples
"""
import sys


def _run_tests() -> None:
    """Validate the spec proof examples from Section 5."""
    from theorem_prover.commands import fact_list, reset_session
    from theorem_prover.display import display_prop
    from theorem_prover.parser import parse_and_run

    examples = [
        # (input_string, expected_display)
        ("succ_not_zero(0)",                                  "0++ ≠ 0"),
        ("flip(succ_not_zero(0))",                            "0 ≠ 0++"),
        ("cont(succ_imp_eq(0, 0++))",                         "0 ≠ 0++ ⇒ 0++ ≠ (0++)++"),
        # Spec 5.3: cont gives 0≠0++ ⇒ 0++≠(0++)++; mp returns the consequent.
        # (The spec example shows the sides flipped — that is a typo in the doc.)
        ("mp(flip(succ_not_zero(0)), cont(succ_imp_eq(0, 0++)))", "0++ ≠ (0++)++"),
        ("add_zero_eq(0)",                                    "0 + 0 = 0"),
        ("flip(add_zero_eq(0))",                              "0 = 0 + 0"),
    ]

    reset_session()
    passed = 0
    failed = 0

    print("Running spec proof examples…\n")
    for cmd, expected in examples:
        reset_session()
        result = parse_and_run(cmd)
        got = display_prop(result)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}]  {cmd}")
        if not ok:
            print(f"         expected: {expected}")
            print(f"         got:      {got}")
            failed += 1
        else:
            passed += 1

    print(f"\n{passed} passed, {failed} failed.")
    sys.exit(0 if failed == 0 else 1)


def main() -> None:
    args = sys.argv[1:]

    if "--test" in args:
        _run_tests()
        return

    if "--repl" in args:
        from theorem_prover.repl import run_repl
        run_repl()
        return

    if "--tui" in args:
        try:
            from theorem_prover.ui import run_ui
            run_ui()
        except ImportError:
            print("Textual not found.  pip install textual")
        return

    # Default: web app
    from server import run_server
    run_server()


if __name__ == "__main__":
    main()
