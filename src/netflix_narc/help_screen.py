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
                "Know what your family is actually watching.",
                classes="help-subtitle",
            )

            with ScrollableContainer(id="help-scroll"):
                # ── What This Is ─────────────────────────────────────────
                yield Static("WHAT THIS IS", classes="help-section-title")
                yield Static(
                    "Netflix tracks everything your household watches. Netflix Narc "
                    "lets you go through that history and flag anything that might "
                    "be too mature — violence, language, adult themes — based on "
                    "standards you define.",
                    classes="help-text",
                )

                # ── How It Works ─────────────────────────────────────────
                yield Static("HOW IT WORKS", classes="help-section-title")
                yield Static(
                    "Every title in your history gets a [b]Suitability Score[/b]. "
                    "You set the bar in [b]Setup[/b] — the age range you're "
                    "screening for, and how much weight to give things like "
                    "violence or language. Anything that doesn't meet your bar "
                    "gets flagged in the main table.",
                    classes="help-text",
                )
                yield Static(
                    "The scores are based on details [i]you[/i] enter for each "
                    "title — the age rating, content categories, and so on. "
                    "[b]The Lineup[/b] is where you do that work, one title at "
                    "a time, without having to scroll through your entire history.",
                    classes="help-text",
                )

                # ── The Screens ───────────────────────────────────────────
                yield Static("THE SCREENS", classes="help-section-title")
                yield Static(
                    "  • [b]The Lineup  [L][/b]\n"
                    "    The best place to start. Surfaces the titles that most\n"
                    "    need your attention — things watched frequently, or with\n"
                    "    no rating yet. Work through them one at a time.",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]Interrogation Room  [I][/b]\n"
                    "    Where you rate a title. Enter its age rating and score\n"
                    "    content like violence, language, and adult themes.\n"
                    "    Your entries are saved and used in every evaluation.",
                    classes="help-bullet",
                )
                yield Static(
                    "  • [b]Setup  [S][/b]\n"
                    "    Where you define your standards. Set the age range\n"
                    "    you're screening for and how strictly each content\n"
                    "    category is penalized.",
                    classes="help-bullet",
                )

                # ── Key Bindings ─────────────────────────────────────────
                yield Static("KEY BINDINGS", classes="help-section-title")
                yield Static(
                    "  [b]L[/b]          Open The Lineup\n"
                    "  [b]I[/b]          Interrogate selected title\n"
                    "  [b]E[/b]          Evaluate all titles\n"
                    "  [b]C[/b]          Load / refresh CSV history\n"
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
