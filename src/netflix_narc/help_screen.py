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
            yield Static("NETFLIX NARC - HELP & ABOUT", classes="help-title")
            yield Static(
                "An inappropriate content detector for your viewing history.",
                classes="help-subtitle",
            )

            with ScrollableContainer(id="help-scroll"):
                yield Static("WHAT IS NETFLIX NARC?", classes="help-section-title")
                yield Static(
                    "Netflix Narc is a CLI/TUI application that ingests your Netflix viewing "
                    "history CSV, queries online APIs (Common Sense Media, OMDb, TMDB) "
                    "for age ratings and category ratings, and flags inappropriate content "
                    "based on your customizable suitability criteria.",
                    classes="help-text",
                )

                yield Static("HOW RATING SUITABILITY WORKS", classes="help-section-title")
                yield Static(
                    "Each title gets a suitability score (from 0% to 100%) calculated "
                    "based on the following:",
                    classes="help-text",
                )
                yield Static(
                    "• [b]Bidirectional Symmetric Age Distance[/b]:\n"
                    "  If you configure a child's age range (e.g. 8-12), content rating is "
                    "  evaluated symmetrically. An exact match or younger rating receives "
                    "  [green]0 deduction[/green]. If content is too mature OR too young "
                    "  for the target range, it receives a penalty of [yellow]1.0[/yellow] "
                    "  per year outside the range, up to a maximum penalty of "
                    "  [red]5.0[/red]. If child_age_range is not configured, the app falls "
                    "  back to legacy behavior (only penalizing too-mature titles by 1.5x "
                    "  excess).",
                    classes="help-bullet",
                )
                yield Static(
                    "• [b]Category Scores & Custom Weights[/b]:\n"
                    "  Evaluates scores for negative categories (Violence, Language, Sexy "
                    "  Stuff, Drinking & Drugs) and positive categories (Educational Value, "
                    "  Positive Messages/Role Models). A higher weight configures the "
                    "  system to be more strictly penalizing.",
                    classes="help-bullet",
                )

                yield Static("THE DISCOVERY QUEUE (THE LINEUP)", classes="help-section-title")
                yield Static(
                    "Press [b][l][/b] on the main screen to start the Lineup. The Lineup ranks "
                    "titles that require investigation based on View Counts, low-quality API "
                    "flags, and dossiers completeness. In the Lineup screen, you can:\n"
                    "  - [b]Skip [S][/b]: Move to the next title in the queue.\n"
                    "  - [b]Ignore [X][/b]: Mark the title as ignored to permanently hide it "
                    "from evaluations.\n"
                    "  - [b]Interrogate [I][/b]: Jump directly to the Interrogation Room to "
                    "manually enter metadata.",
                    classes="help-text",
                )

                yield Static(
                    "THE INTERROGATION ROOM (MANUAL ENTRY)",
                    classes="help-section-title",
                )
                yield Static(
                    "Press [b][i][/b] on the selected table row or lineup title to enter "
                    "manual details. Use this to override online API errors, populate "
                    "missing content ratings, set category scores, and save custom poster "
                    "URLs. This data is saved permanently in your local [b]Evidence "
                    "Locker[/b] (SQLite database) and merged automatically with online "
                    "API data.",
                    classes="help-text",
                )

                yield Static("KEY BINDINGS / CHEAT SHEET", classes="help-section-title")
                yield Static("[b]Main Screen shortcuts:[/b]", classes="help-text")
                yield Static(
                    "  • [b]L[/b]: Open The Lineup (Discovery Queue)",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]C[/b]: Load or Refresh Netflix history CSV file",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]S[/b]: Open Setup / Configuration Settings",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]E[/b]: Bulk evaluate all titles in the table",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]I[/b]: Interrogate the currently selected title",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]?[/b] / [b]H[/b]: Show this Help screen",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]Q[/b] / [b]CTRL+C[/b]: Quit the application",
                    classes="help-bullet",
                )

                yield Static(
                    "\n[dim]Press ESC or Q to return to Netflix Narc.[/dim]",
                    classes="help-text",
                )

        yield Footer()
