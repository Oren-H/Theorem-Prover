"""
Textual TUI for the PA Theorem Prover.

Layout
------
┌──────────────────────────────────────────────────────────┐
│            Peano Arithmetic Theorem Prover               │
├────────────────────────┬─────────────────────────────────┤
│  Facts                 │  Commands                       │
│                        │                                 │
│  #1  0++ ≠ 0           │  succ_not_zero(n)   n++ ≠ 0    │
│  #2  0 ≠ 0++           │  …                              │
│                        │                                 │
├────────────────────────┴─────────────────────────────────┤
│  Terminal                                                │
│  > succ_not_zero(0)                                      │
│    ✓  0++ ≠ 0                                            │
│  ⊢ _                                                     │
└──────────────────────────────────────────────────────────┘

Interactions
------------
- Click a fact row to insert its #N reference into the input.
- Ctrl+R : reset session
- Ctrl+Q : quit
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, RichLog, DataTable, Static
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen

from .commands import fact_list, reset_session
from .display import display_prop
from .parser import parse_and_run
from .errors import InvalidCommand, InvalidInput, TypeMismatch


# ---------------------------------------------------------------------------
# Color palette — warm tan / parchment
# ---------------------------------------------------------------------------
# bg_base     #EDE0C8   main background
# bg_panel    #E3D2B0   slightly darker panel
# bg_term     #F7F0E0   terminal / input area (lightest)
# border      #C8AD87   divider lines
# text        #3A2B1A   primary dark-brown text
# accent      #7A5C38   medium brown (labels, prompt)
# muted       #A8946E   subdued text
# success     #4D7A5A   muted green
# error       #8C3A3A   muted red
# ---------------------------------------------------------------------------

_TAN_CSS = """
/* ── Screen ─────────────────────────────────────────── */
Screen {
    background: #EDE0C8;
    layout: vertical;
}

/* ── Title bar ───────────────────────────────────────── */
#title-bar {
    height: 2;
    background: #B89B6E;
    color: #1E1208;
    content-align: center middle;
    text-style: bold;
}

/* ── Main panels (top portion) ───────────────────────── */
#main-area {
    layout: horizontal;
    height: 3fr;
}

/* Fact list — left */
#fact-panel {
    width: 1fr;
    background: #EDE0C8;
    border-right: solid #C8AD87;
    padding: 1 3 0 3;
}

#fact-label {
    color: #5C3D1E;
    text-style: bold;
    height: 2;
    content-align: left middle;
    border-bottom: solid #C8AD87;
    margin-bottom: 1;
}

DataTable {
    background: #EDE0C8;
    color: #1E1208;
    height: 1fr;
}

DataTable > .datatable--header {
    background: #D4B896;
    color: #1E1208;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #C8AD87;
    color: #1E1208;
    text-style: bold;
}

DataTable > .datatable--even-row {
    background: #EDE0C8;
}

DataTable > .datatable--odd-row {
    background: #E6D4B2;
}

/* Command reference — right */
#cmd-panel {
    width: 1fr;
    background: #E3D2B0;
    padding: 1 3 0 3;
}

#cmd-label {
    color: #5C3D1E;
    text-style: bold;
    height: 2;
    content-align: left middle;
    border-bottom: solid #C8AD87;
    margin-bottom: 1;
}

#cmd-scroll {
    height: 1fr;
    background: #E3D2B0;
}

#cmd-content {
    background: #E3D2B0;
    color: #1E1208;
    padding: 0 0 1 0;
}

/* ── Terminal section (bottom) ───────────────────────── */
#terminal-section {
    height: 2fr;
    layout: vertical;
    border-top: solid #C8AD87;
    background: #F5ECD7;
}

#terminal-label {
    height: 2;
    background: #D4B896;
    color: #5C3D1E;
    text-style: bold;
    padding: 0 2;
    content-align: left middle;
}

#output-log {
    height: 1fr;
    background: #F5ECD7;
    color: #1E1208;
    padding: 1 3;
}

Input {
    background: #F5ECD7;
    color: #1E1208;
    border-top: solid #C8AD87;
    border-bottom: none;
    border-left: none;
    border-right: none;
    padding: 0 3;
    height: 3;
}

Input:focus {
    border-top: solid #5C3D1E;
    border-bottom: none;
    border-left: none;
    border-right: none;
    background: #F5ECD7;
}

Input>.input--placeholder {
    color: #B09060;
}
"""

# ---------------------------------------------------------------------------
# Command reference content (static right panel)
# ---------------------------------------------------------------------------

_CMD_REFERENCE = """\
[bold #5C3D1E]  AXIOMS[/bold #5C3D1E]


  [bold #1E1208]succ_not_zero[/bold #1E1208](n)
    [#7A5C38]n++  ≠  0[/#7A5C38]

  [bold #1E1208]succ_imp_eq[/bold #1E1208](n, m)
    [#7A5C38]n++ = m++  ⇒  n = m[/#7A5C38]

  [bold #1E1208]add_zero_eq[/bold #1E1208](n)
    [#7A5C38]n + 0  =  n[/#7A5C38]

  [bold #1E1208]add_succ_eq[/bold #1E1208](n, m)
    [#7A5C38]n + m++  =  (n+m)++[/#7A5C38]


[bold #5C3D1E]  INFERENCE RULES[/bold #5C3D1E]


  [bold #1E1208]cont[/bold #1E1208](L)
    [#7A5C38]P ⇒ Q   ↦   ¬Q ⇒ ¬P[/#7A5C38]

  [bold #1E1208]mp[/bold #1E1208](P, L)
    [#7A5C38]P,  P ⇒ Q   ⊢   Q[/#7A5C38]

  [bold #1E1208]flip[/bold #1E1208](P)
    [#7A5C38]p = r   ↦   r = p   (also ≠)[/#7A5C38]

  [bold #1E1208]rewrite[/bold #1E1208](eq, target)
    [#7A5C38]substitute one occurrence via eq[/#7A5C38]


[bold #5C3D1E]  NOTATION[/bold #5C3D1E]


  [#7A5C38]0, 1, 2, …      integer  →  Num
  0++, (0++)++    successor
  #N              reference fact N[/#7A5C38]


[bold #5C3D1E]  SHORTCUTS[/bold #5C3D1E]


  [#7A5C38]Ctrl+R     reset session
  Ctrl+Q     quit
  [ / ]      resize fact panel
  click row  insert #N[/#7A5C38]
"""


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

# Fact-panel width steps (percentage of screen width)
_PANEL_WIDTHS = [20, 25, 30, 35, 40, 45, 50, 55, 60]
_DEFAULT_WIDTH_IDX = 4  # 40%


class TheoremProverApp(App):
    CSS = _TAN_CSS

    BINDINGS = [
        Binding("ctrl+r", "reset_session", "Reset"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("[", "shrink_facts", "◀ Facts"),
        Binding("]", "grow_facts", "Facts ▶"),
    ]

    TITLE = "PA Theorem Prover"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._panel_idx = _DEFAULT_WIDTH_IDX

    def compose(self) -> ComposeResult:
        yield Static("Peano Arithmetic Theorem Prover", id="title-bar")

        with Horizontal(id="main-area"):
            # Left: fact list
            with Vertical(id="fact-panel"):
                yield Static("Facts", id="fact-label")
                yield DataTable(
                    id="fact-table",
                    cursor_type="row",
                    zebra_stripes=True,
                    show_header=False,
                )

            # Right: command reference
            with Vertical(id="cmd-panel"):
                yield Static("Commands", id="cmd-label")
                with ScrollableContainer(id="cmd-scroll"):
                    yield Static(_CMD_REFERENCE, id="cmd-content", markup=True)

        # Bottom: terminal
        with Vertical(id="terminal-section"):
            yield Static("Terminal", id="terminal-label")
            yield RichLog(
                id="output-log",
                highlight=False,
                markup=True,
                wrap=True,
            )
            yield Input(placeholder="⊢  enter command…", id="cmd-input")

    def on_mount(self) -> None:
        table = self.query_one("#fact-table", DataTable)
        table.add_columns("", "Proposition")
        self._apply_panel_width()
        self.query_one("#cmd-input", Input).focus()

    # -----------------------------------------------------------------------
    # Panel resize
    # -----------------------------------------------------------------------

    def _apply_panel_width(self) -> None:
        w = _PANEL_WIDTHS[self._panel_idx]
        self.query_one("#fact-panel").styles.width = f"{w}%"

    def action_shrink_facts(self) -> None:
        if self._panel_idx > 0:
            self._panel_idx -= 1
            self._apply_panel_width()

    def action_grow_facts(self) -> None:
        if self._panel_idx < len(_PANEL_WIDTHS) - 1:
            self._panel_idx += 1
            self._apply_panel_width()

    # -----------------------------------------------------------------------
    # Command submission
    # -----------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            return
        log = self.query_one("#output-log", RichLog)
        inp = self.query_one("#cmd-input", Input)
        inp.value = ""

        log.write(f"[bold #5C3D1E]⊢  {raw}[/bold #5C3D1E]")

        if raw.lower() in ("quit", "exit", "q"):
            self.exit()
            return
        if raw.lower() == "reset":
            self.action_reset_session()
            return

        n_before = len(fact_list)
        try:
            parse_and_run(raw)
        except InvalidCommand as e:
            log.write(f"  [bold #8C3A3A]✗[/bold #8C3A3A]  [#8C3A3A]unknown command —  {e}[/#8C3A3A]")
            return
        except InvalidInput as e:
            log.write(f"  [bold #8C3A3A]✗[/bold #8C3A3A]  [#8C3A3A]invalid input —  {e}[/#8C3A3A]")
            return
        except TypeMismatch as e:
            log.write(f"  [bold #8C3A3A]✗[/bold #8C3A3A]  [#8C3A3A]type mismatch —  {e}[/#8C3A3A]")
            return
        except Exception as e:
            log.write(f"  [bold #8C3A3A]✗[/bold #8C3A3A]  [#8C3A3A]{e}[/#8C3A3A]")
            return

        new_facts = fact_list[n_before:]
        for prop in new_facts:
            log.write(
                f"  [bold #4D7A5A]✓[/bold #4D7A5A]  "
                f"[bold #1E1208]{display_prop(prop)}[/bold #1E1208]"
            )

        self._refresh_fact_table()

    # -----------------------------------------------------------------------
    # Fact table click → insert #N reference
    # -----------------------------------------------------------------------

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        inp = self.query_one("#cmd-input", Input)
        ref = f"#{event.row_key.value}"
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
        log.write("[#B09060]──  session reset  ──[/#B09060]")

    def _refresh_fact_table(self) -> None:
        table = self.query_one("#fact-table", DataTable)
        table.clear()
        for i, prop in enumerate(fact_list, 1):
            table.add_row(f"#{i}", display_prop(prop), key=str(i))


def run_ui() -> None:
    TheoremProverApp().run()
