# PA Theorem Prover

An interactive theorem prover for **Peano Arithmetic (PA)**. You construct proofs by composing axiom commands and inference rules, and the tool accumulates a numbered list of derived facts that you can reference in subsequent steps.

Three frontends are available: a browser-based web app (default), a terminal UI (TUI), and a plain REPL.

---

## Quick Start

```bash
pip install -r requirements.txt

python main.py              # web app — opens http://127.0.0.1:5050
python main.py --repl       # plain terminal REPL
python main.py --tui        # Textual TUI (requires textual>=0.47)
python main.py --test       # run built-in spec proof examples
```

---

## Commands

### Axioms

| Command | Produces |
|---------|----------|
| `succ_not_zero(n)` | `n++ ≠ 0` |
| `succ_imp_eq(n, m)` | `n++ = m++ ⇒ n = m` |
| `add_zero_eq(n)` | `n + 0 = n` |
| `add_succ_eq(n, m)` | `n + m++ = (n+m)++` |

### Inference Rules

| Command | Effect |
|---------|--------|
| `cont(L)` | Contrapositive: `P ⇒ Q` becomes `¬Q ⇒ ¬P` |
| `mp(P, L)` | Modus ponens: given `P` and `P ⇒ Q`, derives `Q` |
| `flip(P)` | Symmetry: swaps sides of `=` or `≠` |

### Input Notation

| Syntax | Meaning |
|--------|---------|
| `0`, `1`, `2`, … | Integer literals — auto-converted to Peano `Num` |
| `0++`, `(0++)++` | Postfix successor operator |
| `#N` | Reference fact N from the current session's fact list |

Commands can be nested — each nested call is also recorded as a fact:

```
mp(flip(succ_not_zero(0)), cont(succ_imp_eq(0, 0++)))
```

---

## Architecture

```
Theorem Prover/
├── main.py                    # Entry point — dispatches to web/repl/tui/test
├── server.py                  # Flask web server + REST API
├── requirements.txt
├── templates/
│   └── index.html             # Web app HTML
├── static/
│   ├── app.js                 # Web app logic (autocomplete, resize, history)
│   └── style.css              # Web app styles
└── theorem_prover/
    ├── __init__.py
    ├── types.py               # Immutable dataclasses: Term and Prop hierarchies
    ├── validation.py          # Type predicates: check_valid_{num,term,prop}
    ├── errors.py              # Typed exceptions
    ├── commands.py            # Axioms, inference rules, and session state
    ├── parser.py              # Tokeniser + recursive-descent parser
    ├── display.py             # Unicode renderer for Terms and Props
    ├── repl.py                # Plain terminal REPL
    └── ui.py                  # Textual TUI
```

### Core Package (`theorem_prover/`)

#### `types.py` — Type System

The type system is split into two strictly separate hierarchies, both implemented as immutable frozen dataclasses (structural equality and hashing come for free):

```
Term
├── Num
│   ├── Zero           — the constant 0
│   └── Succ(pred)     — successor of another Num
└── Add(left, right)   — addition of two Terms

Prop
├── Eq(left, right)    — left = right
├── Neq(left, right)   — left ≠ right  (syntactic sugar for Not(Eq(...)))
├── Not(prop)          — negation
└── Imp(antecedent, consequent)  — implication ⇒
```

Props are never Terms and vice versa — the validator enforces this boundary at runtime.

#### `commands.py` — Axioms, Inference Rules, and Session State

This module is the semantic core. Every command:
1. Validates its arguments (using `validation.py`)
2. Constructs the resulting `Prop`
3. Appends it to the module-level `fact_list`
4. Returns the new `Prop`

`fact_list` is the single source of truth for the session. `reset_session()` clears it. `COMMANDS` is a registry dict mapping command name strings to `(function, arity)` tuples, which the parser uses for dispatch.

Notable implementation details:
- `_props_equal()` identifies `Neq(x,y)` with `Not(Eq(x,y))` structurally so that `mp()` can match antecedents regardless of which form was used.
- `mp()` raises `TypeMismatch` (a distinct error class) when the supplied prop does not match the implication's antecedent, giving a clear error message showing both sides.

#### `parser.py` — Tokeniser and Recursive-Descent Parser

**Grammar:**
```
command_line  ::= expr EOF
expr          ::= call_expr | paren_expr | int_expr | fact_ref
call_expr     ::= NAME '(' arg_list? ')' plusplus*
paren_expr    ::= '(' expr ')' plusplus*
int_expr      ::= INT plusplus*
fact_ref      ::= '#' INT plusplus*
arg_list      ::= expr (',' expr)*
plusplus       ::= '++'
```

The tokeniser runs first and produces a flat token list. The recursive-descent `Parser` then walks the token list. Key behaviours:
- Integer literals are eagerly converted to the corresponding `Num` via repeated `Succ` wrapping.
- `++` is a postfix successor operator that can be chained: `0++` → `Succ(Zero())`, `(0++)++` → `Succ(Succ(Zero()))`.
- `#N` dereferences fact N (1-indexed) directly from `fact_list` at parse time.
- Nested calls each invoke their command function (and record a fact) as they are parsed — the tree is evaluated during parsing, not in a separate pass.

`parse_and_run(src)` is the single public entry point used by all three frontends.

#### `validation.py` — Type Predicates

Three recursive validators:
- `check_valid_num(x)` — accepts `Zero` or `Succ`
- `check_valid_term(x)` — accepts `Num` or `Add`; explicitly rejects Props with a clear error
- `check_valid_prop(x)` — accepts `Eq`, `Neq`, `Not`, `Imp`; explicitly rejects Terms

All raise `InvalidInput` on failure.

#### `display.py` — Unicode Renderer

`display_term` and `display_prop` recursively render the AST to human-readable Unicode strings using `≠`, `⇒`, `¬`. Parentheses are inserted only where needed for unambiguous reading (e.g., nested `Add` or `Imp`).

#### `errors.py` — Exception Hierarchy

Three typed exceptions allow frontends to give specific error messages:
- `InvalidCommand` — unknown command name
- `InvalidInput` — wrong argument type or bad literal
- `TypeMismatch` — `mp()` antecedent mismatch

---

### Web App (`server.py` + `static/` + `templates/`)

The default frontend. Flask serves a single-page app.

**REST API:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve `index.html` |
| `POST` | `/api/run` | Execute a command; returns `{ok, new_facts, facts}` |
| `POST` | `/api/reset` | Clear the session; returns `{ok, facts: []}` |
| `GET` | `/api/facts` | Return current fact list |

The server translates the three exception types into structured JSON error responses with an `error_type` field, so the client can display appropriate labels ("unknown command", "invalid input", "type mismatch").

**Frontend (`app.js`):**

Layout: a resizable split between a fact panel (left) and a command reference (right), with a terminal section below. Both splits have draggable dividers.

Key features:
- **Autocomplete**: The input is a `contenteditable` div (not `<input>`). A ghost-completion span is injected inline into the same element so the suggestion text aligns exactly with what the user typed. A dropdown shows matching commands. `Tab` cycles through matches; `→` or `Tab` (single match) accepts.
- **Signature help**: When the cursor is inside a function call's argument list, a signature tooltip shows which parameter is active.
- **Command history**: `↑`/`↓` arrows navigate session history; the current draft is preserved when browsing.
- **Fact insertion**: Clicking a fact row inserts `#N` at the cursor position.
- **Keyboard shortcuts**: `Enter` submits, `Ctrl+Shift+R` resets, `Escape` dismisses autocomplete.

---

### Textual TUI (`theorem_prover/ui.py`)

A [Textual](https://textual.textualize.io/) terminal application with the same three-panel layout. Styled with a warm parchment color palette.

**Panels:**
- **Facts** (left): `DataTable` widget with zebra striping; clicking a row inserts `#N` into the input.
- **Commands** (right): Static reference panel with Rich markup.
- **Terminal** (bottom): `RichLog` output + `Input` widget.

**Bindings:** `Ctrl+R` reset, `Ctrl+Q` quit, `[`/`]` resize the fact panel through nine width steps (20%–60%).

---

### Plain REPL (`theorem_prover/repl.py`)

A minimal `input()`-based loop. Imports `readline` when available for arrow-key history. Built-in meta-commands: `help`, `list`, `reset`, `quit`/`exit`.

---

### Entry Point (`main.py`)

Dispatches based on CLI flags:

| Flag | Behaviour |
|------|-----------|
| *(none)* | Launch web app |
| `--repl` | Plain terminal REPL |
| `--tui` | Textual TUI |
| `--test` | Run spec proof examples and exit with pass/fail code |

The `--test` mode runs six reference proofs from the specification and prints a PASS/FAIL report, useful for regression testing.

---

## Data Flow

```
User input (string)
        │
        ▼
  tokenise()  ──────────────────────────────── InvalidInput
        │
        ▼
  Parser.parse_command_line()
        │
        │  for each call_expr encountered:
        │       validate args
        │       construct Prop
        │       append to fact_list   ←── side effect
        │       return Prop
        ▼
  top-level Prop (or Num)
        │
        ▼
  display_prop() / display_term()
        │
        ▼
  rendered string → frontend
```

Because evaluation is interleaved with parsing, a nested expression like `mp(flip(succ_not_zero(0)), ...)` records intermediate facts for `succ_not_zero(0)` and `flip(...)` before the outer `mp` fact is recorded.
