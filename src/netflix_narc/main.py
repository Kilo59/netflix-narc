"""Main entry point for the Netflix Narc application."""

from __future__ import annotations

import argparse
import contextlib
import functools
import pathlib
from typing import TYPE_CHECKING, ClassVar, override

from pydantic import BaseModel, ConfigDict, SecretStr, TypeAdapter
from textual import on, work
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
from netflix_narc.manual_db import EvidenceLocker
from netflix_narc.persistence import load_and_group_history, update_env_file
from netflix_narc.settings import (
    DEFAULT_CSV_FILENAME,
    RatingProviderType,
    Settings,
    SyncBackendType,
    get_config_dir,
)
from netflix_narc.sync import (
    LocalStorageBackend,
    S3StorageBackend,
    StorageBackend,
    StorageBackendError,
    SyncEngine,
    WebDAVStorageBackend,
)

if TYPE_CHECKING:
    from typing import Any

    from textual.binding import Binding

    from netflix_narc.parser import ViewingRecord
    from netflix_narc.rating_api import RatingProvider


def create_storage_backend(config: Settings | SetupConfig) -> StorageBackend | None:
    """Instantiate StorageBackend based on settings or setup config."""
    match config.sync_backend:
        case SyncBackendType.LOCAL_FOLDER:
            path = config.sync_local_path or str(get_config_dir(create=True) / "sync")
            return LocalStorageBackend(path)
        case SyncBackendType.S3:
            if not config.sync_s3_endpoint_url or not config.sync_s3_bucket:
                return None
            return S3StorageBackend(
                endpoint_url=config.sync_s3_endpoint_url,
                bucket_name=config.sync_s3_bucket,
                access_key_id=config.sync_s3_access_key_id,
                secret_access_key=config.sync_s3_secret_access_key,
            )
        case SyncBackendType.WEBDAV:
            if not config.sync_webdav_url or not config.sync_webdav_username:
                return None
            return WebDAVStorageBackend(
                webdav_url=config.sync_webdav_url,
                username=config.sync_webdav_username,
                password=config.sync_webdav_password,
            )
        case _:
            return None


class SetupConfig(BaseModel):
    """Configuration result payload from the setup screen."""

    model_config: ClassVar[ConfigDict] = {"extra": "forbid"}

    provider: RatingProviderType
    api_key: SecretStr
    sync_backend: SyncBackendType = SyncBackendType.OFF
    sync_local_path: str = ""
    sync_s3_endpoint_url: str = ""
    sync_s3_bucket: str = ""
    sync_s3_access_key_id: SecretStr = SecretStr("")
    sync_s3_secret_access_key: SecretStr = SecretStr("")
    sync_webdav_url: str = ""
    sync_webdav_username: str = ""
    sync_webdav_password: SecretStr = SecretStr("")


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
            Static("Storage & Sync (BYOS)", classes="instructions"),
            Select(
                [
                    ("Off (Local Only)", SyncBackendType.OFF),
                    ("Local Folder / iCloud", SyncBackendType.LOCAL_FOLDER),
                    ("Cloudflare R2 / S3", SyncBackendType.S3),
                    ("Nextcloud / WebDAV", SyncBackendType.WEBDAV),
                ],
                value=SyncBackendType.OFF,
                id="sync-backend-select",
            ),
            Input(placeholder="Sync Folder Path (Optional)...", id="sync-local-path-input"),
            Horizontal(
                Button("Test Connection ⚡", id="test-sync-btn"),
                id="test-btn-container",
            ),
            Static("", id="sync-test-result"),
            Horizontal(
                Button("Cancel", variant="error", id="cancel-btn"),
                Button("Save & Continue", variant="primary", id="save-btn"),
            ),
            id="setup-container",
        )

    def _update_sync_test_button_visibility(self) -> None:
        """Show or hide the sync test button depending on backend support."""
        backend_type = self.query_one("#sync-backend-select", Select).value
        test_btn_container = self.query_one("#test-btn-container", Horizontal)
        test_btn_container.display = backend_type != Select.BLANK

    def on_mount(self) -> None:
        """Set initial widget states on mount."""
        self._update_sync_test_button_visibility()

    @on(Select.Changed, "#sync-backend-select")
    def on_sync_backend_select_changed(self, _event: Select.Changed) -> None:
        """Handle changes to the sync backend selection."""
        self._update_sync_test_button_visibility()
        self.query_one("#sync-test-result", Static).update("")

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
        elif event.button.id == "test-sync-btn":
            self._test_connection()

    def _build_config_from_form(self) -> SetupConfig:
        """Construct a SetupConfig payload from current form inputs and app settings."""
        provider = self.query_one("#provider-select", Select).value
        api_key = self.query_one("#api-key-input", Input).value
        sync_backend = self.query_one("#sync-backend-select", Select).value
        local_path = self.query_one("#sync-local-path-input", Input).value

        provider_enum = (
            provider if isinstance(provider, RatingProviderType) else RatingProviderType.OMDB
        )
        secret_key = TypeAdapter(SecretStr).validate_python(api_key or "")
        backend_enum = (
            sync_backend if isinstance(sync_backend, SyncBackendType) else SyncBackendType.OFF
        )

        app_settings = getattr(self.app, "settings", None)
        s3_url = app_settings.sync_s3_endpoint_url if app_settings else ""
        s3_bucket = app_settings.sync_s3_bucket if app_settings else ""
        s3_key = app_settings.sync_s3_access_key_id if app_settings else SecretStr("")
        s3_secret = app_settings.sync_s3_secret_access_key if app_settings else SecretStr("")
        webdav_url = app_settings.sync_webdav_url if app_settings else ""
        webdav_user = app_settings.sync_webdav_username if app_settings else ""
        webdav_pass = app_settings.sync_webdav_password if app_settings else SecretStr("")

        return SetupConfig(
            provider=provider_enum,
            api_key=secret_key,
            sync_backend=backend_enum,
            sync_local_path=local_path,
            sync_s3_endpoint_url=s3_url,
            sync_s3_bucket=s3_bucket,
            sync_s3_access_key_id=s3_key,
            sync_s3_secret_access_key=s3_secret,
            sync_webdav_url=webdav_url,
            sync_webdav_username=webdav_user,
            sync_webdav_password=webdav_pass,
        )

    @work
    async def _test_connection(self) -> None:
        """Asynchronously test the configured storage backend connection."""
        result_label = self.query_one("#sync-test-result", Static)
        result_label.update("[yellow]Testing connection...[/yellow]")

        config = self._build_config_from_form()
        if config.sync_backend == SyncBackendType.OFF:
            result_label.update("[green]🟢 Local storage active (Sync disabled).[/green]")
            return

        backend = create_storage_backend(config)
        if backend is None:
            result_label.update(
                "[red]🔴 Storage configuration incomplete (Check URL/Bucket/Credentials).[/red]"
            )
            return

        try:
            ok = await backend.test_connection()
            if ok:
                result_label.update("[green]🟢 Connection verified successfully![/green]")
            else:
                result_label.update(
                    "[red]🔴 Connection test failed (Check access/permissions).[/red]"
                )
        except StorageBackendError as exc:
            result_label.update(f"[red]🔴 Connection error: {exc}[/red]")

    def _save_settings(self) -> None:
        """Validate and save settings, then dismiss the screen."""
        provider = self.query_one("#provider-select", Select).value
        api_key = self.query_one("#api-key-input", Input).value

        if provider and api_key and isinstance(provider, RatingProviderType):
            config = self._build_config_from_form()
            self.dismiss(config)
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
        self.manual_db = EvidenceLocker(get_config_dir(create=True) / "evidence_locker.sqlite")
        self.sync_engine: SyncEngine | None = None

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

    @work(exclusive=True)
    async def run_background_sync(self) -> None:
        """Run two-way synchronization in the background without blocking UI."""
        if not self.sync_engine:
            return
        await self.manual_db.init()
        res = await self.sync_engine.sync()
        if res.status == "success" and res.items_synced > 0:
            self.notify(f"☁️ Synced {res.items_synced} item(s) with storage.")

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

    def _startup_sync_sequence(self) -> None:
        """Load CSV and perform initial cache-based evaluation on the main thread."""
        self._load_startup_csv()

        needs_settings = not self.rating_provider

        if self.rating_provider:
            for base_title in self.grouped_records:
                if base_title not in self.evaluated_flags:
                    metadata = self.rating_provider.search_title(base_title, cache_only=True)
                    if metadata:
                        flags = evaluate_title(metadata, self.settings)
                        flags_str = (
                            f"[red]{', '.join(flags)}[/red]" if flags else "[green]Passed[/green]"
                        )
                    else:
                        flags_str = "[yellow]Not Found[/yellow]"
                    self.evaluated_flags[base_title] = flags_str

        self._finish_startup(needs_settings=needs_settings)

    def _finish_startup(self, *, needs_settings: bool) -> None:
        """Called from the main thread after the startup worker completes."""
        self.rebuild_table(evaluate=False, cache_only=True)
        self._set_loading(state=False)

        backend = create_storage_backend(self.settings)
        if backend is not None:
            self.sync_engine = SyncEngine(backend, self.manual_db, self.settings)
            self.run_background_sync()

        if needs_settings:
            # We don't need call_after_refresh here because it's already on the main thread
            self.action_settings()

    def action_settings(self) -> None:
        """Push the setup screen to configure API keys."""
        self.push_screen(SetupScreen(), self.handle_setup_complete)

    def handle_setup_complete(self, config: SetupConfig | None) -> None:
        """Handle the completion of the setup screen."""
        if config:
            provider = config.provider
            api_key = config.api_key

            self.settings.active_rating_provider = provider
            self.settings.sync_backend = config.sync_backend
            self.settings.sync_local_path = config.sync_local_path

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
                extra_env = {
                    "SYNC_BACKEND": str(config.sync_backend),
                    "SYNC_LOCAL_PATH": config.sync_local_path,
                }
                update_env_file(
                    provider,
                    api_key,
                    pathlib.Path(".env"),
                    extra_env=extra_env,
                )

                backend = create_storage_backend(self.settings)
                if backend is not None:
                    self.sync_engine = SyncEngine(backend, self.manual_db, self.settings)
                    self.run_background_sync()

                self.notify(f"Settings saved for {provider.upper()}.")
            except (ValueError, NotImplementedError) as e:
                self.notify(f"Initialization error: {e}", severity="error")

    def action_load_csv(self) -> None:
        """Load the Netflix history from a CSV file."""
        # Use the configured path, or fall back to the default filename
        csv_to_load = self.csv_path or DEFAULT_CSV_FILENAME
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

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Ensure loading indicator is hidden if a worker fails or is cancelled."""
        if event.state in (WorkerState.ERROR, WorkerState.CANCELLED):
            self._set_loading(state=False)

    def load_data(self, filepath: str) -> None:
        """Load and parse Netflix viewing history from the given path."""
        try:
            grouped = load_and_group_history(pathlib.Path(filepath), self.settings.max_records)
            self.grouped_records.clear()
            self.grouped_records.update(grouped)
            self.rebuild_table()
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
        help=f"Path to your {DEFAULT_CSV_FILENAME} file.",
    )
    args = parser.parse_args()

    settings = Settings()
    app = NetflixNarcApp(settings=settings, csv_path=args.csv_path)
    app.run()


if __name__ == "__main__":
    main()
