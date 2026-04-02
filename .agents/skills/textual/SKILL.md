---
name: textual
description: How to use the Textual framework for creating Terminal User Interfaces (TUIs) in Python
---

# Textual TUI Framework

Textual is an async Rapid Application Development framework for Python that allows you to build sophisticated user interfaces in the terminal using an API inspired by modern web development.

## Core Concepts

1. **The App Class**: Every Textual application inherits from `textual.app.App`.
2. **Widgets**: Reusable components like `Static`, `Button`, `Input`, `DataTable`, etc. available under `textual.widgets`.
3. **The `compose` Method**: Instead of explicitly appending children to a layout, Textual uses generator functions (`yield`) to compose the UI hierarchically.
4. **Events and Handlers**: Actions like button presses are handled using structured naming conventions attached to the Widget class names, e.g., `def on_button_pressed(self, event: Button.Pressed)`.
5. **CSS Styling (TCSS)**: A stylesheet language identical to CSS but specialized for the terminal. Layout units use specific constraints like percentages (`100%`) or fractions (`1fr`). *Note: Fractional units are `fr`, not `rf`.*

## Example Application Structure

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Vertical, Horizontal

class MyTextualApp(App):
    # Bind hotkeys to actions (key, action_name, description)
    BINDINGS = [
        ("q", "quit", "Quit application")
    ]

    # Declare the relative path for the stylesheet
    CSS_PATH = "styles.tcss"

    def compose(self) -> ComposeResult:
        """Yield widgets to build the UI."""
        yield Header()

        # Structure layout via Containers that act like CSS flexboxes
        yield Vertical(
            Static("Welcome to Textual!", id="welcome-text"),
            Horizontal(
                Button("Click Me!", id="say-hello-btn", variant="primary"),
            ),
        )

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event Handler fired when any button is pressed."""
        if event.button.id == "say-hello-btn":
            self.notify("Hello World!")

    def action_quit(self) -> None:
        """Action handler corresponding to the BINDING 'quit'."""
        self.exit()

if __name__ == "__main__":
    app = MyTextualApp()
    app.run()
```

## Styling via TCSS Example

TCSS rules map component classes, IDs, and elements just like standard web CSS, providing a responsive design engine for terminal grids.

```css
#welcome-text {
    content-align: center middle;
    text-style: bold;
    color: $accent;
    padding: 1 2;
}

Horizontal {
    height: auto;
}

Button {
    width: 1fr; /* Use 'fr' units for fractional flexible widths across the parent container */
}
```

## Modal Screens

Applications can overlay completely distinct views or modals via `Screen` objects:

```python
from textual.screen import Screen

class SetupScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Static("Settings Configurator")
        yield Button("Save", id="save-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Dismissing a screen pops it off the stack and optionally returns a payload
        self.dismiss("Saved Data Payload")

# Inside your main application class:
def open_setup(self):
    self.push_screen(SetupScreen(), callback=self.on_setup_completed)


def on_setup_completed(self, payload: str):
    self.notify(f"Setup returned: {payload}")
```

## Official Documentation & Reference

For more detailed information, consult the official Textual documentation:

- [Reference](https://textual.textualize.io/reference/): Comprehensive guides and concept explanations.
- [Guide](https://textual.textualize.io/guide/): Step-by-step tutorials to get started.
- [How-to](https://textual.textualize.io/how-to/): Specific recipes for common tasks.
- [FAQ](https://textual.textualize.io/FAQ/): Answers to frequently asked questions.
- [API Reference](https://textual.textualize.io/api/): Detailed documentation for the Textual Python API.
