"""
Textual TUI for the PA Theorem Prover.

Layout
------
┌─────────────────────────────────────────────────────────┐
│  PA Theorem Prover                          [Header]    │
├──────────────────────────────┬──────────────────────────┤
│  Fact List                   │  Session Output          │
│  ─────────────────           │  ───────────────         │
│  #1  0++ ≠ 0                 │  > succ_not_zero(0)      │
│  #2  0 ≠ 0++                 │    ✓  0++ ≠ 0            │
│  …                           │  > …                     │
│                              │                          │
├──────────────────────────────┴──────────────────────────┤
│  ⊢ _                                        [Input]     │
└─────────────────────────────────────────────────────────┘

Interactions
------------
- Click a fact row to copy it as a #N reference into the input.
- Type commands exactly as in the REPL; errors appear inline.
- F1 / ? : toggle help overlay
- Ctrl+R : reset session
- Ctrl+C / q : quit
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import (
    Header,
    Footer,
    Input,
    RichLog,
    DataTable,
    Static,
)
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen

from .commands import fact_list, reset_session
from .display import display_prop
from .parser import parse_and_run
from .errors import InvalidCommand, InvalidInput, TypeMismatch
from .types import Zero, Succ, Add


HELP_TEXT = """\
[bold]PA Theorem Prover — Command Reference[/bold]

[bold yellow]Axioms[/bold yellow]
  succ_not_zero(n)      n++ ≠ 0
  succ_imp_eq(n, m)     n++ = m++ ⇒ n = m
  add_zero_eq(n)        n + 0 = n
  add_succ_eq(n, m)     n + m++ = (n+m)++

[bold yellow]Inference rules[/bold yellow]
  cont(L)               contrapositive of implication L  (P⇒Q  ↦  ¬Q⇒¬P)
  mp(P, L)              modus ponens: P, P⇒Q ⊢ Q
  flip(P)               symmetry:  p = r  ↦  r = p  (also Neq)

[bold yellow]Input notation[/bold yellow]
  0, 1, 2, …            integer literals (auto-converted to Num)
  0++, (0++)++, …       successor notation
  #N                    reference fact N from the fact list

[bold yellow]Keyboard shortcuts[/bold yellow]
  F1 / ?                toggle this help panel
  Ctrl+R                reset session (clear all facts)
  Ctrl+Q / q            quit
  Enter                 submit command
  Click a fact row      insert #N reference into the input field
"""


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape,f1,question_mark", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT, id="help-content")

    def on_mount(self) -> None:
        self.query_one("#help-content").styles.padding = (1, 2)
        self.query_one("#help-content").styles.background = "black"
        self.query_one("#help-content").styles.border = ("round", "yellow")
        self.query_one("#help-content").styles.width = "70%"
        self.query_one("#help-content").styles.height = "auto"
        self.query_one("#help-content").styles.margin = (4, 0)
        self.query_one("#help-content").styles.align = ("center", "middle")


class TheoremProverApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #main-area {
        layout: horizontal;
        height: 1fr;
    }

    #fact-panel {
        width: 40%;
        border: solid $accent;
        padding: 0 1;
    }

    #fact-panel-title {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }

    #fact-table {
        height: 1fr;
    }

    #output-panel {
        width: 60%;
        border: solid $accent;
        padding: 0 1;
    }

    #output-panel-title {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }

    #output-log {
        height: 1fr;
    }

    #input-bar {
        height: 3;
        padding: 0 1;
        border-top: solid $accent;
    }

    #cmd-input {
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+r", "reset_session", "Reset"),
        Binding("f1,question_mark", "show_help", "Help"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    TITLE = "PA Theorem Prover"
    SUB_TITLE = "Peano Arithmetic  |  F1 for help"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-area"):
            with Vertical(id="fact-panel"):
                yield Static("Fact List", id="fact-panel-title")
                yield DataTable(id="fact-table", cursor_type="row", zebra_stripes=True)
            with Vertical(id="output-panel"):
                yield Static("Session Output", id="output-panel-title")
                yield RichLog(id="output-log", highlight=True, markup=True, wrap=True)
        with Horizontal(id="input-bar"):
            yield Input(placeholder="Enter command… (F1 for help)", id="cmd-input")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#fact-table", DataTable)
        table.add_columns("#", "Proposition")
        log = self.query_one("#output-log", RichLog)
        log.write("[dim]Session started. Type a command and press Enter.[/dim]")
        self.query_one("#cmd-input", Input).focus()

    # -----------------------------------------------------------------------
    # Input handling
    # -----------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            return
        log = self.query_one("#output-log", RichLog)
        inp = self.query_one("#cmd-input", Input)
        inp.value = ""

        log.write(f"[bold cyan]⊢ {raw}[/bold cyan]")

        # Built-in meta-commands
        if raw.lower() in ("quit", "exit", "q"):
            self.exit()
            return
        if raw.lower() in ("help", "?"):
            self.action_show_help()
            return
        if raw.lower() == "reset":
            self.action_reset_session()
            return
        if raw.lower() == "list":
            if not fact_list:
                log.write("[dim]  (no facts yet)[/dim]")
            else:
                for i, p in enumerate(fact_list, 1):
                    log.write(f"  [green]#{i}[/green]  {display_prop(p)}")
            return

        # Parse and evaluate
        n_before = len(fact_list)
        try:
            result = parse_and_run(raw)
        except InvalidCommand as e:
            log.write(f"[red bold][unknown command][/red bold]  {e}")
            return
        except InvalidInput as e:
            log.write(f"[red bold][invalid input][/red bold]  {e}")
            return
        except TypeMismatch as e:
            log.write(f"[red bold][type mismatch][/red bold]  {e}")
            return
        except Exception as e:
            log.write(f"[red bold][error][/red bold]  {e}")
            return

        # Display all newly added facts
        new_facts = fact_list[n_before:]
        for prop in new_facts:
            log.write(f"  [green]✓[/green]  {display_prop(prop)}")

        # Refresh the fact table
        self._refresh_fact_table()
        log.write("")

    def _refresh_fact_table(self) -> None:
        table = self.query_one("#fact-table", DataTable)
        table.clear()
        for i, prop in enumerate(fact_list, 1):
            table.add_row(f"#{i}", display_prop(prop), key=str(i))

    # -----------------------------------------------------------------------
    # Fact table click → insert reference
    # -----------------------------------------------------------------------

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Click a fact row to insert its #N reference into the input."""
        inp = self.query_one("#cmd-input", Input)
        ref = f"#{event.row_key.value}"
        # Insert at cursor position or append.
        cursor = inp.cursor_position
        current = inp.value
        inp.value = current[:cursor] + ref + current[cursor:]
        inp.cursor_position = cursor + len(ref)
        inp.focus()

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------

    def action_reset_session(self) -> None:
        reset_session()
        self._refresh_fact_table()
        log = self.query_one("#output-log", RichLog)
        log.write("[yellow]── Session reset ──[/yellow]")

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())


def run_ui() -> None:
    app = TheoremProverApp()
    app.run()
