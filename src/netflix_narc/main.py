"""Main entry point for the Netflix Narc application."""

from __future__ import annotations

import argparse
import contextlib
import functools
import pathlib
from typing import TYPE_CHECKING, ClassVar, NamedTuple, override

from pydantic import SecretStr, TypeAdapter
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
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
from netflix_narc.parser import ViewingRecord, parse_netflix_history
from netflix_narc.settings import RatingProviderType, Settings

if TYPE_CHECKING:
    from typing import Any

    from textual.binding import Binding

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


class NetflixNarcApp(App[None]):
    """A Textual TUI for viewing and evaluating Netflix history."""

    CSS_PATH = "narc.tcss"
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("f10", "quit", "Quit"),
        ("l", "load_csv", "Load CSV"),
        ("s", "settings", "Settings"),
        ("e", "evaluate", "Evaluate Titles"),
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

        # State for grouping history
        self.grouped_records: dict[str, list[ViewingRecord]] = {}
        self.expanded_titles: set[str] = set()
        self.evaluated_flags: dict[str, str] = {}

    @override
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Horizontal():
            yield DataTable(id="history-table")

        indicator = LoadingIndicator(id="loading-indicator")
        indicator.display = False
        yield indicator

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
        table.add_column("Flags")

        # Load CSV: prefer explicit path, then fall back to default filename
        csv_to_load = self.csv_path or pathlib.Path("NetflixViewingHistory.csv")
        if csv_to_load.exists():
            self.load_data(str(csv_to_load))

        has_any_key = bool(
            self.settings.csm_api_key.get_secret_value()
            or self.settings.omdb_api_key.get_secret_value()
            or self.settings.tmdb_api_key.get_secret_value()
        )

        if has_any_key:
            try:
                self.rating_provider = get_rating_provider(settings=self.settings)
                # Auto-evaluate on startup but ONLY from cache (don't hit network)
                self.rebuild_table(evaluate=True, cache_only=True)
            except (ValueError, NotImplementedError) as e:
                self.notify(f"Error initializing provider: {e}", severity="error")
        else:
            # No API keys configured — guide the user through setup automatically
            self.call_after_refresh(self.action_settings)

    def action_settings(self) -> None:
        """Push the setup screen to configure API keys."""
        self.push_screen(SetupScreen(), self.handle_setup_complete)

    def _parse_env_line(
        self, raw_line: str, new_values: dict[str, str], seen_keys: set[str]
    ) -> str | None:
        """Parse a single .env line and return the updated version, or None if skipped."""
        line = raw_line.strip()
        if not line or line.startswith("#"):
            return line

        if "=" in line:
            k, _ = line.split("=", 1)
            if k in new_values:
                seen_keys.add(k)
                return f"{k}={new_values[k]}"
            return line
        return line

    def _update_env_file(self, provider: RatingProviderType, api_key: SecretStr) -> None:
        """Update the .env file with new provider settings, deduplicating keys."""
        env_path = pathlib.Path(".env")
        env_lines = []
        if env_path.exists():
            env_lines = env_path.read_text().splitlines()

        # Map prefix to new value
        new_values = {
            "ACTIVE_RATING_PROVIDER": str(provider),
        }
        if provider == RatingProviderType.CSM:
            new_values["CSM_API_KEY"] = api_key.get_secret_value()
        elif provider == RatingProviderType.OMDB:
            new_values["OMDB_API_KEY"] = api_key.get_secret_value()

        # Process existing lines, updating matches
        updated_lines = []
        seen_keys: set[str] = set()
        for raw_line in env_lines:
            updated_line = self._parse_env_line(raw_line, new_values, seen_keys)
            if updated_line is not None:
                updated_lines.append(updated_line)

        # Add new keys that weren't in the file
        for k, v in new_values.items():
            if k not in seen_keys:
                updated_lines.append(f"{k}={v}")

        # Write atomically
        temp_env = env_path.with_suffix(".tmp")
        temp_env.write_text("\n".join(updated_lines) + "\n")
        temp_env.replace(env_path)

    def handle_setup_complete(self, config: SetupConfig | None) -> None:
        """Handle the completion of the setup screen.

        Args:
            config: The configured provider and API key, if any.
        """
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
                self.rating_provider = get_rating_provider(settings=self.settings)
                self._update_env_file(provider, api_key)
                self.notify(f"Settings saved for {provider.upper()}.")
            except (ValueError, NotImplementedError) as e:
                self.notify(f"Initialization error: {e}", severity="error")

    def action_load_csv(self) -> None:
        """Load the Netflix history from a CSV file."""
        # Use the configured path, or fall back to the default filename
        csv_to_load = self.csv_path or pathlib.Path("NetflixViewingHistory.csv")
        self.load_data(str(csv_to_load))

    def action_evaluate(self) -> None:
        """Evaluate the loaded history against the active rating provider."""
        if not self.rating_provider:
            self.notify("Please configure an API Key first (`s`).", severity="warning")
            self.action_settings()
            return

        self.notify("Evaluating displayed titles...")
        self.run_worker(
            functools.partial(self._evaluate_titles_worker, cache_only=False),
            exclusive=True,
            thread=True,
        )

    def _evaluate_titles_worker(self, *, cache_only: bool) -> None:
        """Worker: evaluate all ungrouped titles off the main thread.

        Runs in a background thread. Calls back to the main thread via
        `call_from_thread` after each title so the table updates progressively.

        Args:
            cache_only: If True, only use responses already in the hishel cache.
        """
        provider = self.rating_provider
        if provider is None:
            return

        self.call_from_thread(self._set_loading, state=True)

        titles = list(self.grouped_records.keys())
        for base_title in titles:
            if base_title in self.evaluated_flags:
                continue

            metadata = provider.search_title(base_title, cache_only=cache_only)
            if metadata:
                flags = evaluate_title(metadata, self.settings)
                flags_str = f"[red]{', '.join(flags)}[/red]" if flags else "[green]Passed[/green]"
            else:
                flags_str = "[yellow]Not Found[/yellow]"

            self.evaluated_flags[base_title] = flags_str
            self.call_from_thread(self._update_row_flags, base_title, flags_str)

        self.call_from_thread(self._set_loading, state=False)

    def _set_loading(self, *, state: bool) -> None:
        """Show or hide the loading indicator (must be called from main thread)."""
        self.query_one(LoadingIndicator).display = state

    def _update_row_flags(self, base_title: str, flags_str: str) -> None:
        """Update the Flags cell for a specific row (must be called from main thread)."""
        table = self.query_one(DataTable)
        with contextlib.suppress(Exception):
            # Row key is the base_title string -- update column index 2 (Flags)
            # Row may not exist if table was rebuilt; safe to ignore.
            table.update_cell(base_title, "flags", flags_str, update_width=False)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Ensure loading indicator is hidden if a worker fails or is cancelled."""
        if event.state in (WorkerState.ERROR, WorkerState.CANCELLED):
            self._set_loading(state=False)

    def load_data(self, filepath: str) -> None:
        """Load and parse Netflix viewing history from the given path."""
        try:
            records: list[ViewingRecord] = parse_netflix_history(pathlib.Path(filepath))

            # Group records by base title
            self.grouped_records.clear()
            for record in records[:200]:  # loading more for context
                base_title = record.title.split(":")[0].strip()
                if base_title not in self.grouped_records:
                    self.grouped_records[base_title] = []
                self.grouped_records[base_title].append(record)

            self.rebuild_table()
        except FileNotFoundError as e:
            self.notify(f"History file not found: {e}", severity="error")
        except ValueError as e:
            self.notify(f"Error parsing CSV: {e}", severity="error")

    def rebuild_table(
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
        table = self.query_one(DataTable)
        table.clear()

        for base_title, records in self.grouped_records.items():
            flags_str = self.evaluated_flags.get(base_title, "None")

            if evaluate and self.rating_provider and base_title not in self.evaluated_flags:
                metadata = self.rating_provider.search_title(base_title, cache_only=cache_only)
                if metadata:
                    flags = evaluate_title(metadata, self.settings)
                    flags_str = (
                        f"[red]{', '.join(flags)}[/red]" if flags else "[green]Passed[/green]"
                    )
                else:
                    flags_str = "[yellow]Not Found[/yellow]"
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
                    table.add_row(
                        rec.date_watched.strftime("%Y-%m-%d"),
                        f"  └─ {rec.title}",
                        "",
                        key=f"{base_title}_{rec.title}_{rec.date_watched.isoformat()}",
                    )

        if cursor_to_key:
            with contextlib.suppress(Exception):
                table.cursor_coordinate = (table.get_row_index(cursor_to_key), 0)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the data table."""
        row_key = event.row_key.value

        # We only toggle parent rows (base titles)
        if row_key and isinstance(row_key, str) and row_key in self.grouped_records:
            if row_key in self.expanded_titles:
                self.expanded_titles.remove(row_key)
            else:
                self.expanded_titles.add(row_key)
            self.rebuild_table(evaluate=False, cursor_to_key=row_key)


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
        help="Path to your NetflixViewingHistory.csv file.",
    )
    args = parser.parse_args()

    settings = Settings()
    app = NetflixNarcApp(settings=settings, csv_path=args.csv_path)
    app.run()


if __name__ == "__main__":
    main()
