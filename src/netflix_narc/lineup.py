"""The Lineup Screen for iterating through Netflix viewing history."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, ClassVar, cast, override

from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from netflix_narc.interrogation_room import InterrogationRoomScreen

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from netflix_narc.main import NetflixNarcApp
    from netflix_narc.parser import ViewingRecord


class LineupScreen(Screen[None]):
    """The Lineup Screen: sequentially review titles in the queue."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("q", "app.pop_screen", "Quit Lineup"),
        Binding("i", "interrogate", "Interrogate"),
        Binding("x", "ignore", "Ignore"),
        Binding("s", "skip", "Skip"),
    ]

    def __init__(
        self,
        queue: list[str],
        grouped_records: dict[str, list[ViewingRecord]] | None = None,
        completeness_map: dict[str, int] | None = None,
    ) -> None:
        """Initialize the lineup screen.

        Args:
            queue: The sorted list of titles to display.
            grouped_records: Optional dictionary to look up viewing dates and counts.
            completeness_map: Map of title -> dossier completeness score (0-100).
        """
        super().__init__()
        self.queue = queue
        self.grouped_records = grouped_records or {}
        self.completeness_map = completeness_map or {}
        self.current_index = 0
        self._background_tasks: set[asyncio.Task[None]] = set()

    @property
    def narc_app(self) -> NetflixNarcApp:
        """Type-safe access to the main app."""
        return cast("NetflixNarcApp", self.app)

    @override
    def compose(self) -> ComposeResult:
        """Compose the child widgets for the Lineup Screen."""
        yield Header()
        with Container(id="lineup-container"), Vertical(id="lineup-card"):
            yield Static(id="lineup-counter")
            yield Static(id="title-info")

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
        records = self.grouped_records.get(base_title, [])
        date_list = [r.date_watched.strftime("%Y-%m-%d") for r in records if r.date_watched]
        first_watched = min(date_list) if date_list else "Unknown"
        last_watched = max(date_list) if date_list else "Unknown"

        completeness = self.completeness_map.get(base_title, 0)
        bars = int(completeness / 10)
        progress_bar = f"[{'█' * bars}{'░' * (10 - bars)}] {completeness}%"

        info = f"""[b]Title:[/b] {base_title}
[b]Views:[/b] {len(records)}
[b]First Watched:[/b] {first_watched}
[b]Last Watched:[/b] {last_watched}

[b]Dossier Completeness:[/b] {progress_bar}"""

        self.query_one("#lineup-counter", Static).update(
            f"Title {self.current_index + 1} of {len(self.queue)}"
        )
        self.query_one("#title-info", Static).update(info)

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

        # Update the main data table instantly
        await self.narc_app.refresh_title(base_title)
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
