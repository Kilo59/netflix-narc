from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from netflix_narc.csm_api import CSMClient
from netflix_narc.evaluator import evaluate_title
from netflix_narc.parser import ViewingRecord, parse_netflix_history
from netflix_narc.settings import Settings


class SetupScreen(Container):
    """A screen prompting for initial configuration (API Key, etc.)."""

    def compose(self) -> ComposeResult:
        # In a real app, this would use Inputs to gather the API key and weights,
        # then save them using a dotenv or config writer.
        yield Static("Welcome to Netflix Narc!", classes="title")
        yield Static(
            "Please configure your Common Sense Media API key via the "
            "`CSM_API_KEY` environment variable.",
            classes="instructions",
        )


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
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("l", "load_csv", "Load CSV"),
    ]

    def __init__(self, csv_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.csv_path = csv_path

        # Load settings (reads from environment variables / .env)
        # Using a dummy fallback for now if running locally without keys
        self.settings = Settings(csm_api_key="dummy_key_for_ui_dev")
        self.csm_client = CSMClient(settings=self.settings)

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
        table.add_columns("Date Watched", "Title", "Flags")

        if self.csv_path:
            self.load_data(self.csv_path)

    def action_load_csv(self) -> None:
        """An action to load a hardcoded or prompted CSV file."""
        # Hardcoding the local path for this iteration based on user context
        self.load_data("NetflixViewingHistory.csv")

    def load_data(self, filepath: str) -> None:
        table = self.query_one(DataTable)
        table.clear()

        try:
            records: list[ViewingRecord] = parse_netflix_history(filepath)

            # For demonstration, we'll only load the first 50 to avoid hammering the mock
            # In real usage, the background worker would yield these progressively.
            for record in records[:50]:
                # Mock Fetch Metadata
                metadata = self.csm_client.search_title(record.title)

                flags_str = "None"
                row_style = ""

                if metadata:
                    flags = evaluate_title(metadata, self.settings)
                    if flags:
                        flags_str = ", ".join(flags)
                        # We use textual styling or just raw text for now
                        flags_str = f"[red]{flags_str}[/red]"

                table.add_row(record.date_watched.strftime("%Y-%m-%d"), record.title, flags_str)
        except Exception as e:
            self.notify(f"Error loading CSV: {e}", severity="error")


if __name__ == "__main__":
    app = NetflixNarcApp(csv_path="NetflixViewingHistory.csv")
    app.run()
