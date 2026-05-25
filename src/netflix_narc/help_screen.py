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
                "Flag inappropriate content in your Netflix viewing history.",
                classes="help-subtitle",
            )

            with ScrollableContainer(id="help-scroll"):
                # ── Quick Start ──────────────────────────────────────────
                yield Static("QUICK START", classes="help-section-title")
                yield Static(
                    "  [b]1.[/b]  Export your Netflix history from "
                    "[i]Account → Viewing Activity → Download All[/i].\n"
                    "  [b]2.[/b]  Press [b]C[/b] to load the downloaded CSV file.\n"
                    "  [b]3.[/b]  Press [b]E[/b] to evaluate all titles.\n"
                    "  [b]4.[/b]  Flagged titles appear highlighted in the table.",
                    classes="help-text",
                )

                # ── What It Does ─────────────────────────────────────────
                yield Static("WHAT IT DOES", classes="help-section-title")
                yield Static(
                    "Netflix Narc fetches age ratings and content scores from "
                    "Common Sense Media (CSM), OMDb, and TMDB, then calculates "
                    "a [b]Suitability Score[/b] for each title based on your "
                    "settings. Titles that fall below the threshold are flagged.",
                    classes="help-text",
                )

                # ── Screens ──────────────────────────────────────────────
                yield Static("SCREENS", classes="help-section-title")
                yield Static(
                    "  • [b]Main Table[/b] — Your full viewing history with "
                    "suitability scores. Select a row and press [b]I[/b] to "
                    "enter manual data for a title.",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]The Lineup[/b] — Press [b]L[/b] to open a guided "
                    "queue of titles that need attention (missing ratings, "
                    "high view counts, incomplete data). Work through them "
                    "one at a time.",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]Interrogation Room[/b] — Manually set a title's "
                    "content rating, category scores, and poster URL. Useful "
                    "when API data is missing or wrong. Changes are saved "
                    "locally and merged automatically on the next evaluation.",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]Setup[/b] — Press [b]S[/b] to configure your API "
                    "keys, suitability threshold, category weights, and "
                    "child age range.",
                    classes="help-bullet",
                )

                # ── Key Bindings ─────────────────────────────────────────
                yield Static("KEY BINDINGS", classes="help-section-title")
                yield Static(
                    "  [b]C[/b]   Load / refresh CSV history\n"
                    "  [b]E[/b]   Evaluate all titles\n"
                    "  [b]L[/b]   Open The Lineup\n"
                    "  [b]I[/b]   Interrogate selected title\n"
                    "  [b]S[/b]   Open Setup\n"
                    "  [b]?[/b] / [b]H[/b]   Show this screen\n"
                    "  [b]Q[/b] / [b]ESC[/b]   Go back / Quit",
                    classes="help-text",
                )

                yield Static(
                    "\n[dim]Press ESC or Q to return to Netflix Narc.[/dim]",
                    classes="help-text",
                )

        yield Footer()
