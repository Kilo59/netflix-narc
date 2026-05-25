"""Main entry point for the Netflix Narc application."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import pathlib
import webbrowser
from typing import TYPE_CHECKING, ClassVar, NamedTuple, override

from pydantic import SecretStr, TypeAdapter
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    Select,
    Static,
)
from textual.worker import Worker, WorkerState

from netflix_narc.evaluator import evaluate_title
from netflix_narc.factory import get_rating_provider
from netflix_narc.interrogation_room import InterrogationRoomScreen
from netflix_narc.lineup import LineupScreen
from netflix_narc.manual_db import EvidenceLocker
from netflix_narc.persistence import load_and_group_history, update_env_file
from netflix_narc.settings import DEFAULT_CSV_FILENAME, RatingProviderType, Settings

if TYPE_CHECKING:
    from typing import Any

    from textual.binding import Binding

    from netflix_narc.parser import ViewingRecord
    from netflix_narc.rating_api import RatingProvider


class SetupConfig(NamedTuple):
    """Configuration result from the setup screen."""

    provider: RatingProviderType
    api_key: SecretStr


class SetupScreen(Screen[SetupConfig | None]):
    """A screen prompting for initial configuration (Provider, API Key)."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "cancel", "Cancel"),
    ]

    @override
    def compose(self) -> ComposeResult:
        """Compose the setup screen widgets."""
        yield Container(
            Static("Welcome to Netflix Narc!", classes="title"),
            Static(
                "Choose your rating provider and enter your API key.",
                classes="instructions",
            ),
            Select(
                [(p.name.replace("_", " "), p) for p in RatingProviderType],
                value=RatingProviderType.OMDB,
                id="provider-select",
            ),
            Input(placeholder="Enter API Key...", id="api-key-input", password=True),
            Horizontal(
                Button("Cancel", variant="error", id="cancel-btn"),
                Button("Save & Continue", variant="primary", id="save-btn"),
            ),
            id="setup-container",
        )

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Save settings when Enter is pressed on the Input widget."""
        self._save_settings()

    def action_cancel(self) -> None:
        """Handle escape key to cancel."""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events in the setup screen."""
        if event.button.id == "save-btn":
            self._save_settings()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def _save_settings(self) -> None:
        """Validate and save settings, then dismiss the screen."""
        provider = self.query_one("#provider-select", Select).value
        api_key = self.query_one("#api-key-input", Input).value
        if provider and api_key and isinstance(provider, RatingProviderType):
            secret_key = TypeAdapter(SecretStr).validate_python(api_key)
            self.dismiss(SetupConfig(provider=provider, api_key=secret_key))
        else:
            self.notify("Provider and API Key required", severity="warning")


class LoadCsvScreen(Screen[str | None]):
    """A screen prompting to load or refresh the ViewingHistory.csv."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, current_path: pathlib.Path) -> None:
        """Initialize the screen with the current CSV path."""
        super().__init__()
        self.current_path = current_path

    @override
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Load Viewing History", classes="title"),
            Static(
                "Need to refresh your data? Download your history from Netflix.",
                classes="instructions",
            ),
            Button("Open Download Instructions", variant="default", id="btn-help"),
            Static("Place it here or specify the path below:", classes="instructions"),
            Input(value=str(self.current_path), id="csv-path-input"),
            Horizontal(
                Button("Cancel", variant="error", id="cancel-btn"),
                Button("Load Data", variant="primary", id="load-btn"),
            ),
            id="setup-container",
        )

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Load the given path when Enter is pressed."""
        self._load()

    def action_cancel(self) -> None:
        """Handle escape key to cancel."""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "load-btn":
            self._load()
        elif event.button.id == "btn-help":
            webbrowser.open("https://help.netflix.com/en/node/101917")
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def _load(self) -> None:
        csv_path = self.query_one("#csv-path-input", Input).value
        if csv_path:
            self.dismiss(csv_path)
        else:
            self.notify("Please enter a path to the CSV.", severity="warning")


class NetflixNarcApp(App[None]):
    """A Textual TUI for viewing and evaluating Netflix history."""

    CSS_PATH = "narc.tcss"
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("f10", "quit", "Quit"),
        ("l", "start_lineup", "The Lineup"),
        ("c", "load_csv", "Load CSV"),
        ("s", "settings", "Settings"),
        ("e", "evaluate", "Evaluate Titles"),
        ("i", "interrogate", "Interrogate Title"),
    ]

    def __init__(
        self,
        settings: Settings,
        csv_path: pathlib.Path | None = None,
        cache_dir: pathlib.Path | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the Netflix Narc application.

        Args:
            settings: Configuration settings for the application.
            csv_path: Optional path to the Netflix viewing history CSV.
            cache_dir: Optional directory for HTTP caching.
            **kwargs: Additional keyword arguments for the Textual App.
        """
        super().__init__(**kwargs)
        self.settings = settings
        self.csv_path = csv_path
        self.cache_dir = cache_dir
        self.rating_provider: RatingProvider | None = None

        db_path = (
            (self.cache_dir / "evidence_locker.sqlite")
            if self.cache_dir
            else "evidence_locker.sqlite"
        )
        self.evidence_locker = EvidenceLocker(db_path)

        # State for grouping history
        self.grouped_records: dict[str, list[ViewingRecord]] = {}
        self.expanded_titles: set[str] = set()
        self.evaluated_flags: dict[str, str] = {}

    @override
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Container(id="main-container"):
            yield DataTable(id="history-table")
            with Container(id="loading-overlay"):
                yield LoadingIndicator()
                yield Static("Narcing on your Netflix viewing history...", id="loading-message")

        yield Footer()

    def on_unmount(self) -> None:
        """Close the rating provider when the app exits."""
        if self.rating_provider:
            self.rating_provider.close()

    def on_mount(self) -> None:
        """Configure the data table on mount."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_column("Date Watched", width=15)
        table.add_column("Title", width=45)
        table.add_column("Flags", key="flags")

        # Show loading indicator while background worker initializes
        has_any_key = bool(
            self.settings.csm_api_key.get_secret_value()
            or self.settings.omdb_api_key.get_secret_value()
            or self.settings.tmdb_api_key.get_secret_value()
        )
        if has_any_key:
            try:
                self.rating_provider = get_rating_provider(
                    settings=self.settings, cache_dir=self.cache_dir
                )
            except (ValueError, NotImplementedError) as e:
                self.notify(f"Error initializing provider: {e}", severity="error")

        self._set_loading(state=True)
        # Yield to the event loop so the loading indicator renders before blocking work
        self.call_after_refresh(self._startup_sync_sequence)

    def _load_startup_csv(self) -> None:
        """Helper to load and group the CSV data synchronously on startup."""
        csv_to_load = self.csv_path or DEFAULT_CSV_FILENAME
        if not csv_to_load.exists():
            return
        try:
            grouped = load_and_group_history(csv_to_load, self.settings.max_records)
            self.grouped_records.clear()
            self.grouped_records.update(grouped)
        except (OSError, ValueError) as e:
            self.notify(f"Error parsing CSV: {e}", severity="error")

    async def _startup_sync_sequence(self) -> None:
        """Load CSV and perform initial cache-based evaluation on the main thread."""
        self._load_startup_csv()

        for base_title in self.grouped_records:
            if base_title not in self.evaluated_flags:
                flags_str = await self._fetch_and_evaluate(base_title, cache_only=True)
                self.evaluated_flags[base_title] = flags_str

        await self._finish_startup()

    async def _finish_startup(self) -> None:
        """Called from the main thread after the startup worker completes."""
        await self.evidence_locker.init()
        await self.rebuild_table(evaluate=False, cache_only=True)
        self._set_loading(state=False)

    def action_settings(self) -> None:
        """Push the setup screen to configure API keys."""
        self.push_screen(SetupScreen(), self.handle_setup_complete)

    def handle_setup_complete(self, config: SetupConfig | None) -> None:
        """Handle the completion of the setup screen."""
        if config:
            provider = config.provider
            api_key = config.api_key

            self.settings.active_rating_provider = provider
            match provider:
                case RatingProviderType.CSM:
                    self.settings.csm_api_key = api_key
                case RatingProviderType.OMDB:
                    self.settings.omdb_api_key = api_key
                case RatingProviderType.TMDB:
                    self.settings.tmdb_api_key = api_key

            try:
                self.rating_provider = get_rating_provider(
                    settings=self.settings, cache_dir=self.cache_dir
                )
                update_env_file(provider, api_key, pathlib.Path(".env"))
                self.notify(f"Settings saved for {provider.upper()}.")
            except (ValueError, NotImplementedError) as e:
                self.notify(f"Initialization error: {e}", severity="error")

    def action_load_csv(self) -> None:
        """Push the Load CSV screen."""
        self.push_screen(
            LoadCsvScreen(self.csv_path or pathlib.Path(DEFAULT_CSV_FILENAME)),
            self.handle_load_csv_complete,
        )

    async def handle_load_csv_complete(self, new_path: str | None) -> None:
        """Handle the completion of the Load CSV screen."""
        if new_path:
            await self.load_data(new_path)

    def action_evaluate(self) -> None:
        """Evaluate the loaded history against the active rating provider."""
        if not self.rating_provider:
            self.notify("Please configure an API Key first (`s`).", severity="warning")
            self.action_settings()
            return

        self.notify("Evaluating displayed titles...")

        async def run_eval() -> None:
            await self._evaluate_titles_worker(cache_only=False)

        self.run_worker(run_eval, exclusive=True)  # type: ignore[arg-type]

    async def action_start_lineup(self) -> None:
        """Start the Lineup Screen with the sorted queue."""
        await self._sort_queue()
        queue = list(self.grouped_records.keys())

        all_records = await self.evidence_locker.get_all_records()
        completeness_map = {r.title: r.completeness_score for r in all_records}

        self.push_screen(LineupScreen(queue=queue, completeness_map=completeness_map))

    async def _evaluate_titles_worker(self, *, cache_only: bool) -> None:
        """Worker: evaluate all ungrouped titles.

        Runs as an async worker on the main event loop.
        """
        self._set_loading(state=True)

        titles = list(self.grouped_records.keys())
        for base_title in titles:
            if base_title in self.evaluated_flags:
                continue

            flags_str = await self._fetch_and_evaluate(base_title, cache_only=cache_only)

            self.evaluated_flags[base_title] = flags_str
            self._update_row_flags(base_title, flags_str)

        self._set_loading(state=False)

    def _set_loading(self, *, state: bool) -> None:
        """Show or hide the loading overlay and toggle table visibility."""
        overlay = self.query_one("#loading-overlay", Container)
        table = self.query_one("#history-table", DataTable)

        overlay.display = state
        table.display = not state

    def _update_row_flags(self, base_title: str, flags_str: str) -> None:
        """Update the Flags cell for a specific row (must be called from main thread)."""
        table = self.query_one(DataTable)
        with contextlib.suppress(Exception):
            # Row key is the base_title string -- update column index 2 (Flags)
            # Row may not exist if table was rebuilt; safe to ignore.
            table.update_cell(base_title, "flags", flags_str, update_width=False)

    async def refresh_title(self, base_title: str) -> None:
        """Re-evaluates a single title from cache/manual data and updates the DataTable."""
        flags_str = await self._fetch_and_evaluate(base_title, cache_only=True)
        self.evaluated_flags[base_title] = flags_str
        self._update_row_flags(base_title, flags_str)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Ensure loading indicator is hidden if a worker fails or is cancelled."""
        if event.state in (WorkerState.ERROR, WorkerState.CANCELLED):
            self._set_loading(state=False)

    async def load_data(self, filepath: str) -> None:
        """Load and parse Netflix viewing history from the given path."""
        try:
            grouped = load_and_group_history(pathlib.Path(filepath), self.settings.max_records)
            self.grouped_records.clear()
            self.grouped_records.update(grouped)
            await self.rebuild_table()
        except FileNotFoundError as e:
            self.notify(f"History file not found: {e}", severity="error")
        except ValueError as e:
            self.notify(f"Error parsing CSV: {e}", severity="error")

    def _get_display_title(self, full_title: str, base_title: str) -> str:
        """Strip the redundant show name prefix from a nested title for cleaner display."""
        if full_title.startswith(base_title):
            pruned = full_title[len(base_title) :].lstrip(": ").strip()
            if pruned:
                return pruned
        return full_title

    async def rebuild_table(
        self,
        *,
        evaluate: bool = False,
        cache_only: bool = False,
        cursor_to_key: str | None = None,
    ) -> None:
        """Rebuild the data table with current grouped records.

        For non-evaluate rebuilds (e.g. expand/collapse), previously fetched
        flags are re-used from `self.evaluated_flags` without hitting the network.
        For full evaluation calls, use `action_evaluate` which delegates to the
        background worker.
        """
        await self._sort_queue()
        table = self.query_one(DataTable)
        table.clear()

        for base_title, records in self.grouped_records.items():
            flags_str = self.evaluated_flags.get(base_title, "None")

            if evaluate and self.rating_provider and base_title not in self.evaluated_flags:
                flags_str = await self._fetch_and_evaluate(base_title, cache_only=cache_only)
                self.evaluated_flags[base_title] = flags_str

            indicator = "▼" if base_title in self.expanded_titles else "▶"
            table.add_row(
                f"{len(records)} views",
                f"{indicator} {base_title}",
                flags_str,
                key=base_title,
            )

            if base_title in self.expanded_titles:
                for rec in records:
                    display_title = self._get_display_title(rec.title, base_title)
                    table.add_row(
                        rec.date_watched.strftime("%Y-%m-%d"),
                        f"  └─ {display_title}",
                        "",
                        key=f"{base_title}_{rec.title}_{rec.date_watched.isoformat()}",
                    )

        if cursor_to_key:
            with contextlib.suppress(Exception):
                table.cursor_coordinate = Coordinate(table.get_row_index(cursor_to_key), 0)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the data table."""
        row_key = event.row_key.value

        # We only toggle parent rows (base titles)
        if row_key and isinstance(row_key, str) and row_key in self.grouped_records:
            if row_key in self.expanded_titles:
                self.expanded_titles.remove(row_key)
            else:
                self.expanded_titles.add(row_key)
            await self.rebuild_table(evaluate=False, cursor_to_key=row_key)

    def action_interrogate(self) -> None:
        """Interrogate the currently selected row in the data table."""
        table = self.query_one(DataTable)
        try:
            if not table.cursor_coordinate:
                return
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        except (LookupError, ValueError):
            return

        if not row_key or not isinstance(row_key, str):
            return

        base_title = row_key
        if base_title not in self.grouped_records:
            # Check if it's a child row. Child keys format: {base_title}_{rec.title}_{date}
            for b_title in self.grouped_records:
                if base_title.startswith(b_title + "_"):
                    base_title = b_title
                    break

        if base_title in self.grouped_records:
            self.push_screen(InterrogationRoomScreen(base_title=base_title))

    async def _fetch_and_evaluate(self, base_title: str, *, cache_only: bool) -> str:  # noqa: C901
        """Fetch metadata, merge manual data, and evaluate."""
        manual_record = await self.evidence_locker.get_record(base_title)

        if manual_record and manual_record.ignored:
            return "[dim]Ignored[/dim]"

        api_metadata = None
        if self.rating_provider:
            api_metadata = await asyncio.to_thread(
                self.rating_provider.search_title, base_title, cache_only=cache_only
            )

        # Merge strategy
        if self.settings.merge_manual_data and manual_record:
            if api_metadata is None:
                api_metadata = manual_record.to_normalized_metadata()
            else:
                if manual_record.content_rating is not None:
                    api_metadata.content_rating = manual_record.content_rating
                if manual_record.user_rating is not None:
                    api_metadata.user_rating = manual_record.user_rating
                for cat, val in manual_record.category_scores.items():
                    api_metadata.category_scores[cat] = val
        elif manual_record and not self.settings.merge_manual_data:
            api_metadata = manual_record.to_normalized_metadata()

        if api_metadata:
            flags = evaluate_title(api_metadata, self.settings)

            # Surface if flagged manually
            followup_tag = (
                "[cyan](Flagged)[/cyan] "
                if manual_record and manual_record.flagged_for_followup
                else ""
            )

            if flags:
                return f"{followup_tag}[red]{', '.join(flags)}[/red]"
            return f"{followup_tag}[green]Passed[/green]"

        return "[yellow]Not Found[/yellow]"

    async def _sort_queue(self) -> None:
        """Sort grouped records based on priority queue rules."""
        manual_records = {}
        all_records = await self.evidence_locker.get_all_records()
        for r in all_records:
            manual_records[r.title] = r

        def sort_key(item: tuple[str, list[ViewingRecord]]) -> tuple[int, int, int, int]:
            base_title, records = item

            # 1. Completeness Score (ascending, so 0% comes first)
            manual_record = manual_records.get(base_title)
            completeness = manual_record.completeness_score if manual_record else 0

            # 2. Flagged for follow up
            is_flagged = 1 if manual_record and manual_record.flagged_for_followup else 0

            # 3. Low Quality API flags
            flags_str = self.evaluated_flags.get(base_title, "")
            is_low_quality = 1 if "Low Quality" in flags_str else 0

            # 4. View Count (descending)
            views = len(records)

            return (completeness, -is_flagged, -is_low_quality, -views)

        sorted_items = sorted(self.grouped_records.items(), key=sort_key)
        self.grouped_records.clear()
        self.grouped_records.update(sorted_items)


def main() -> None:
    """CLI Entrypoint to start the Netflix Narc application."""
    parser = argparse.ArgumentParser(
        prog="netflix-narc",
        description="A terminal UI that narcs on inappropriate Netflix viewing history.",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        type=pathlib.Path,
        default=None,
        metavar="PATH",
        help=f"Path to your {DEFAULT_CSV_FILENAME} file.",
    )
    args = parser.parse_args()

    settings = Settings()
    app = NetflixNarcApp(settings=settings, csv_path=args.csv_path)
    app.run()


if __name__ == "__main__":
    main()
