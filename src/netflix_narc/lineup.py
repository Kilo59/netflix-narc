"""The Lineup Screen for iterating through Netflix viewing history."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, override

from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from netflix_narc.interrogation_room import InterrogationRoomScreen

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from netflix_narc.main import NetflixNarcApp


class LineupScreen(Screen[None]):
    """The Lineup Screen: sequentially review titles in the queue."""

    BINDINGS = [  # type: ignore[assignment]
        Binding("q", "app.pop_screen", "Quit Lineup"),
        Binding("i", "interrogate", "Interrogate"),
        Binding("x", "ignore", "Ignore"),
        Binding("s", "skip", "Skip"),
    ]

    def __init__(self, queue: list[str]) -> None:
        """Initialize the screen with a sorted queue of titles."""
        super().__init__()
        self.queue = queue
        self.current_index = 0
        self._background_tasks: set[asyncio.Task[None]] = set()

    @property
    def narc_app(self) -> NetflixNarcApp:
        """Type-safe access to the main app."""
        from typing import cast

        return cast("NetflixNarcApp", self.app)

    @override
    def compose(self) -> ComposeResult:
        """Compose the child widgets for the Lineup Screen."""
        yield Header()
        with Container(id="lineup-container"):
            with Vertical(id="lineup-card"):
                yield Static(id="lineup-counter")
                yield Static(id="lineup-title", classes="title-text")
                yield Static(id="lineup-date", classes="meta-text")
                yield Static(id="lineup-flags", classes="meta-text")

            with Horizontal(id="lineup-actions"):
                yield Button("Interrogate [I]", id="btn-interrogate", variant="primary")
                yield Button("Ignore [X]", id="btn-ignore", variant="warning")
                yield Button("Skip [S]", id="btn-skip", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        """Load the initial UI state when mounted."""
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        if self.current_index >= len(self.queue):
            self.notify("The Lineup is empty!")
            self.app.pop_screen()
            return

        base_title = self.queue[self.current_index]
        records = self.narc_app.grouped_records.get(base_title, [])
        date_str = records[0].date_watched.strftime("%Y-%m-%d") if records else "Unknown"
        flags_str = self.narc_app.evaluated_flags.get(base_title, "None")

        self.query_one("#lineup-counter", Static).update(
            f"Title {self.current_index + 1} of {len(self.queue)}"
        )
        self.query_one("#lineup-title", Static).update(f"Title: {base_title}")
        self.query_one("#lineup-date", Static).update(f"Date Watched: {date_str}")
        self.query_one("#lineup-flags", Static).update(f"API Flags: {flags_str}")

    def action_interrogate(self) -> None:
        """Trigger the Interrogation Room screen for manual entry."""
        if self.current_index >= len(self.queue):
            return
        base_title = self.queue[self.current_index]
        self.app.push_screen(
            InterrogationRoomScreen(base_title), self.handle_interrogation_complete
        )

    def handle_interrogation_complete(self, saved: bool | None) -> None:  # noqa: FBT001
        """Called when the Interrogation Room is closed."""
        if saved:
            self.current_index += 1
            self._refresh_ui()

    async def action_ignore(self) -> None:
        """Mark the title as ignored in the Evidence Locker and skip."""
        if self.current_index >= len(self.queue):
            return
        base_title = self.queue[self.current_index]
        locker = self.narc_app.evidence_locker
        await locker.ignore_title(base_title)

        # Mark as ignored in UI cache so the main table sees it
        self.narc_app.evaluated_flags[base_title] = "[dim]Ignored[/dim]"
        self.notify(f"Ignored: {base_title}")

        self.current_index += 1
        self._refresh_ui()

    def action_skip(self) -> None:
        """Skip this title for now and move to the next."""
        if self.current_index >= len(self.queue):
            return
        self.current_index += 1
        self._refresh_ui()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Map button presses to their respective actions."""
        if event.button.id == "btn-interrogate":
            self.action_interrogate()
        elif event.button.id == "btn-ignore":
            task = asyncio.create_task(self.action_ignore())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        elif event.button.id == "btn-skip":
            self.action_skip()
