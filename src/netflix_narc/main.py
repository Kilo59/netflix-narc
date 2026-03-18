from collections.abc import Sequence
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from netflix_narc.evaluator import evaluate_title
from netflix_narc.factory import get_rating_provider
from netflix_narc.parser import ViewingRecord, parse_netflix_history
from netflix_narc.settings import Settings


class SetupScreen(Screen):
    """A screen prompting for initial configuration (API Key, etc.)."""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Welcome to Netflix Narc!", classes="title"),
            Static(
                "Please configure your Common Sense Media API key.",
                classes="instructions",
            ),
            Input(placeholder="Enter CSM API Key...", id="api-key-input", password=True),
            Horizontal(
                Button("Cancel", variant="error", id="cancel-btn"),
                Button("Save & Continue", variant="primary", id="save-btn"),
            ),
            id="setup-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            api_input = self.query_one("#api-key-input", Input).value
            if api_input:
                self.dismiss(api_input)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class DetailsSidebar(Vertical):
    """Sidebar for configuring weights dynamically."""

    def compose(self) -> ComposeResult:
        yield Static("Settings & Criteria", classes="sidebar-title")
        yield Static("Max Age: 12", classes="sidebar-item")
        yield Static("Min Quality: 3", classes="sidebar-item")
        yield Static("---", classes="sidebar-item")
        yield Static("Violence Weight: High", classes="sidebar-item")
        yield Static("Language Weight: Med", classes="sidebar-item")
        # In the future, these would be interactive sliders/inputs bound to `Settings`.


class NetflixNarcApp(App):
    """A Textual TUI for viewing and evaluating Netflix history."""

    CSS_PATH = "narc.tcss"
    BINDINGS: ClassVar[Sequence[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
        ("l", "load_csv", "Load CSV"),
        ("s", "settings", "Settings"),
        ("e", "evaluate", "Evaluate Titles"),
    ]

    def __init__(self, csv_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.csv_path = csv_path

        # Load settings (reads from environment variables / .env)
        self.settings = Settings()
        self.rating_provider = None

        # State for grouping history
        self.grouped_records: dict[str, list[ViewingRecord]] = {}
        self.expanded_titles: set[str] = set()
        self.evaluated_flags: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Horizontal():
            yield DetailsSidebar(id="sidebar")
            yield DataTable(id="history-table")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Date Watched", "Title", "Flags")

        if self.csv_path:
            self.load_data(self.csv_path)

        if self.settings.csm_api_key or self.settings.omdb_api_key or self.settings.tmdb_api_key:
            try:
                self.rating_provider = get_rating_provider(settings=self.settings)
            except Exception as e:
                self.notify(f"Error initializing provider: {e}", severity="error")

    def action_settings(self) -> None:
        self.push_screen(SetupScreen(), self.handle_setup_complete)

    def handle_setup_complete(self, api_key: str | None) -> None:
        """Callback when the SetupScreen is dismissed."""
        if api_key:
            # For now, we assume setup sets the CSM key as primary
            self.settings.csm_api_key = api_key
            self.rating_provider = get_rating_provider(settings=self.settings)

            # Save to .env for persistence
            with open(".env", "a") as f:
                f.write(f"\nCSM_API_KEY={api_key}\n")
            self.notify("API Key saved.")

    def action_load_csv(self) -> None:
        """An action to load a hardcoded or prompted CSV file."""
        # Hardcoding the local path for this iteration based on user context
        self.load_data("NetflixViewingHistory.csv")

    def action_evaluate(self) -> None:
        """Evaluate the loaded history against the active rating provider."""
        if not self.rating_provider:
            self.notify("Please configure an API Key first (`s`).", severity="warning")
            self.action_settings()
            return

        self.notify("Evaluating displayed titles...")
        self.rebuild_table(evaluate=True)

    def load_data(self, filepath: str) -> None:
        try:
            records: list[ViewingRecord] = parse_netflix_history(filepath)

            # Group records by base title
            self.grouped_records.clear()
            for record in records[:200]:  # loading more for context
                base_title = record.title.split(":")[0].strip()
                if base_title not in self.grouped_records:
                    self.grouped_records[base_title] = []
                self.grouped_records[base_title].append(record)

            self.rebuild_table()
        except Exception as e:
            self.notify(f"Error loading CSV: {e}", severity="error")

    def rebuild_table(self, *, evaluate: bool = False) -> None:
        table = self.query_one(DataTable)
        table.clear()

        for base_title, records in self.grouped_records.items():
            flags_str = self.evaluated_flags.get(base_title, "None")

            if evaluate and self.rating_provider and base_title not in self.evaluated_flags:
                metadata = self.rating_provider.search_title(base_title)
                if metadata:
                    flags = evaluate_title(metadata, self.settings)
                    if flags:
                        flags_str = f"[red]{', '.join(flags)}[/red]"
                    else:
                        flags_str = "[green]Passed[/green]"
                else:
                    flags_str = "[yellow]Not Found[/yellow]"
                self.evaluated_flags[base_title] = flags_str

            indicator = "▼" if base_title in self.expanded_titles else "▶"
            table.add_row(
                f"{len(records)} views", f"{indicator} {base_title}", flags_str, key=base_title
            )

            if base_title in self.expanded_titles:
                for rec in records:
                    table.add_row(
                        rec.date_watched.strftime("%Y-%m-%d"),
                        f"  └─ {rec.title}",
                        "",
                        key=f"{base_title}_{rec.title}_{rec.date_watched.isoformat()}",
                    )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key.value

        # We only toggle parent rows (base titles)
        if row_key and isinstance(row_key, str) and row_key in self.grouped_records:
            if row_key in self.expanded_titles:
                self.expanded_titles.remove(row_key)
            else:
                self.expanded_titles.add(row_key)
            self.rebuild_table(evaluate=False)


def main() -> None:
    """CLI Entrypoint to start the Netflix Narc application."""
    app = NetflixNarcApp(csv_path="NetflixViewingHistory.csv")
    app.run()


if __name__ == "__main__":
    main()
