# Installation Guide

**netflix-narc** is available both as a standalone single-file executable (no Python installation required) and as a standard Python package. Choose the method that best fits your workflow.

---

## Option A: Standalone Executable (Recommended)

Standalone binaries are pre-compiled for macOS, Linux, and Windows. They require **no Python environment setup** and run out of the box.

1. Navigate to the latest release on [GitHub Releases](https://github.com/Kilo59/netflix-narc/releases).
2. Download the binary matching your operating system:
   - **macOS (Apple Silicon / Intel)**: `netflix-narc-macos`
   - **Linux (x86_64)**: `netflix-narc-linux`
   - **Windows (x86_64)**: `netflix-narc-windows.exe`

### Platform-Specific Setup Notes

=== "macOS"

    Because standalone executables downloaded from GitHub are not signed by an Apple Developer Certificate, macOS Gatekeeper may display a warning: `"netflix-narc cannot be opened because it is from an unidentified developer"`.

    To allow execution, open your **Terminal** app and remove the quarantine attribute:

    ```bash
    # 1. Make the binary executable
    chmod +x ~/Downloads/netflix-narc-macos

    # 2. Clear Apple quarantine attribute
    xattr -d com.apple.quarantine ~/Downloads/netflix-narc-macos

    # 3. Optional: Move to your local PATH
    mv ~/Downloads/netflix-narc-macos /usr/local/bin/netflix-narc
    ```

=== "Linux"

    Grant execute permissions and launch from your terminal:

    ```bash
    chmod +x ~/Downloads/netflix-narc-linux
    mv ~/Downloads/netflix-narc-linux ~/.local/bin/netflix-narc
    ```

=== "Windows"

    Launch `netflix-narc-windows.exe` directly from PowerShell or Command Prompt:

    ```powershell
    .\netflix-narc-windows.exe
    ```

---

## Option B: Python Package (`uv` or `pip`)

If you already have Python (≥ 3.13) installed on your computer, you can install `netflix-narc` via `uv` or `pip`.

=== "Using uv (Recommended)"

    [`uv`](https://docs.astral.sh/uv/) installs `netflix-narc` in an isolated tool environment:

    ```bash
    uv tool install netflix-narc
    ```

=== "Using pip"

    Standard installation via PyPI:

    ```bash
    pip install netflix-narc
    ```

---

## Verifying Installation

Verify that `netflix-narc` is installed correctly by running the help command in your terminal:

```bash
netflix-narc --help
```

You should see the command-line usage instructions and available options.
