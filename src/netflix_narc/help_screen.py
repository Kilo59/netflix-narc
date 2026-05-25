"""The Help Screen for Netflix Narc."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class HelpScreen(Screen[None]):
    """A screen displaying details about Netflix Narc, its features, and usage."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "app.pop_screen", "Close Help"),
        Binding("q", "app.pop_screen", "Close Help"),
    ]

    @override
    def compose(self) -> ComposeResult:
        """Compose the help screen widgets."""
        yield Header()
        with Container(id="help-container"), Vertical(id="help-card"):
            yield Static("NETFLIX NARC", classes="help-title")
            yield Static(
                "Review your Netflix history for age-inappropriate content.",
                classes="help-subtitle",
            )

            with ScrollableContainer(id="help-scroll"):
                # ── Getting Started ──────────────────────────────────────
                yield Static("GETTING STARTED", classes="help-section-title")
                yield Static(
                    "  [b]1.[/b]  On Netflix, go to [i]Account → Viewing Activity[/i]\n"
                    "       and click [i]Download all[/i] to get your history CSV.\n"
                    "  [b]2.[/b]  Press [b]C[/b] to load that file into the app.\n"
                    "  [b]3.[/b]  Press [b]L[/b] to open [b]The Lineup[/b] — a queue\n"
                    "       of titles to review one by one.\n"
                    "  [b]4.[/b]  For each title, press [b]I[/b] to open the\n"
                    "       [b]Interrogation Room[/b] and enter its age rating\n"
                    "       and content details yourself.\n"
                    "  [b]5.[/b]  Press [b]E[/b] to score everything. Flagged titles\n"
                    "       will be highlighted in the main table.",
                    classes="help-text",
                )

                # ── Screens ──────────────────────────────────────────────
                yield Static("SCREENS", classes="help-section-title")
                yield Static(
                    "  • [b]The Lineup  [L][/b]\n"
                    "    A guided queue of titles that need your attention.\n"
                    "    Skip, Ignore, or Interrogate each one in turn.",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]Interrogation Room  [I][/b]\n"
                    "    Enter a title's age rating and content scores manually.\n"
                    "    Your entries are saved locally and used in every evaluation.",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]Setup  [S][/b]\n"
                    "    Set your suitability threshold, child age range, and\n"
                    "    category weights. API keys are optional — the app works\n"
                    "    without them using only your manual entries.",
                    classes="help-bullet",
                )

                # ── Key Bindings ─────────────────────────────────────────
                yield Static("KEY BINDINGS", classes="help-section-title")
                yield Static(
                    "  [b]C[/b]          Load / refresh CSV history\n"
                    "  [b]L[/b]          Open The Lineup\n"
                    "  [b]I[/b]          Interrogate selected title\n"
                    "  [b]E[/b]          Evaluate all titles\n"
                    "  [b]S[/b]          Open Setup\n"
                    "  [b]?[/b] / [b]H[/b]      Show this screen\n"
                    "  [b]Q[/b] / [b]ESC[/b]    Go back / Quit",
                    classes="help-text",
                )

                yield Static(
                    "\n[dim]Press ESC or Q to return to Netflix Narc.[/dim]",
                    classes="help-text",
                )

        yield Footer()
