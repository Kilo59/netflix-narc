# Installation Guide

**netflix-narc** is available both as a standalone single-file executable (no Python installation required) and as a standard Python package. Choose the method that best fits your workflow.

---

## Option A: Standalone Executable (Recommended — No Python Required)

Standalone pre-compiled release binaries are available for macOS, Linux, and Windows. They require **no Python environment setup** and run out of the box.

### 1. Download Release Archive

Navigate to the latest release on [GitHub Releases](https://github.com/Kilo59/netflix-narc/releases/latest) and download the archive matching your operating system and architecture:

| Operating System | Architecture | Release Archive Name |
|------------------|--------------|----------------------|
| **macOS** | Apple Silicon (M1/M2/M3/M4) | `netflix-narc-aarch64-apple-darwin.tar.gz` |
| **macOS** | Intel | `netflix-narc-x86_64-apple-darwin.tar.gz` |
| **Linux** | x86_64 | `netflix-narc-x86_64-unknown-linux-gnu.tar.gz` |
| **Windows** | x86_64 | `netflix-narc-x86_64-pc-windows-msvc.zip` |

### 2. Extraction & Platform Notes

=== "macOS"

    1. Extract the downloaded archive:
       ```bash
       tar -xzf netflix-narc-aarch64-apple-darwin.tar.gz
       ```
    2. **Clear Apple Quarantine Attribute**: Because release binaries are not signed with an Apple Developer Certificate, macOS Gatekeeper blocks unnotarized browser downloads with `"netflix-narc Not Opened: Apple could not verify..."` and terminates execution with `killed`. Run:
       ```bash
       xattr -d com.apple.quarantine netflix-narc
       ```
    3. Run the binary directly:
       ```bash
       ./netflix-narc
       ```
    4. *(Optional)* Move to system path:
       ```bash
       sudo mv netflix-narc /usr/local/bin/
       ```

=== "Linux"

    1. Extract the archive and grant execution permissions:
       ```bash
       tar -xzf netflix-narc-x86_64-unknown-linux-gnu.tar.gz
       chmod +x netflix-narc
       ```
    2. Run or move to local path:
       ```bash
       mv netflix-narc ~/.local/bin/
       ```

=== "Windows"

    1. Extract `netflix-narc-x86_64-pc-windows-msvc.zip` (or the raw `.exe`).
    2. Launch from Command Prompt or PowerShell:
       ```powershell
       .\netflix-narc.exe
       ```

### 3. Verifying Download Integrity (SHA256)

Each release includes an official `SHA256SUMS` manifest file. You can verify checksums before executing:

```bash
# macOS
shasum -a 256 -c SHA256SUMS

# Linux
sha256sum -c SHA256SUMS
```

---

## Option B: Python Package (`uv`, `pipx`, `pip`, or Source)

If you have Python (≥ 3.13) installed on your system, you can install **netflix-narc** into an isolated Python environment.

=== "Via uv (Recommended)"

    [`uv`](https://docs.astral.sh/uv/) installs `netflix-narc` into an isolated tool environment:

    ```bash
    uv tool install netflix-narc
    ```

=== "Via pipx"

    ```bash
    pipx install netflix-narc
    ```

=== "Via pip"

    ```bash
    pip install netflix-narc
    ```

=== "From GitHub Source"

    Install the cutting-edge main branch directly from GitHub:

    ```bash
    uv tool install git+https://github.com/Kilo59/netflix-narc
    ```

---

## Verifying Installation

Verify that `netflix-narc` is installed correctly by checking the CLI help flags:

```bash
netflix-narc --help
```
