# Netflix Narc 🕵️‍♂️🍿

![Netflix Narc Hero Art](./assets/hero.png)

**Your automated, terminal-based snitch.**

Netflix Narc is a fast, beautiful Terminal UI built to ingest your family's Netflix viewing history, cross-reference it with the **Common Sense Media API**, and gently narc on anyone watching something they shouldn't.

Whether it's too violent, contains sketchy language, or is just completely devoid of educational value, you decide the criteria, and Netflix Narc tells you who's been watching it.

## ✨ Features

- **🍿 Netflix History Integration**: Ingest your profile's `NetflixViewingHistory.csv` to analyze watching habits.
- **📋 Onboarding Wizard**: First-run setup to configure child age ranges, content weightings, and scoring modes with a live **Weight Impact Preview**.
- **🔍 The Lineup & Interrogation Room**: A Steam-inspired priority review queue (`l`) and manual data entry room (`i`) to score niche titles across Common Sense Media categories (0–5), attach cover art via macOS clipboard, and track dossier completeness.
- **🧠 Common Sense Intel**: Automatically fetches age ratings, quality scores, and granular category breakdowns (Violence, Language, Educational Value, etc.) from API providers (OMDb, CSM, TMDB) or your local Evidence Locker.
- **📊 Suitability Sub-bars & Scoring Modes**: Expand any show to view rich sub-bar breakdowns across Base Quality, Age Suitability, Educational Suitability, Positive Content, and Content Safety under **Quality Focus** or **Balanced** scoring modes.
- **⚖️ Weighted Justice**: Customize how strictly you want to judge different content categories.
- **☁️ Storage & Sync (BYOS)**: Sync preferences and Evidence Locker manual dossiers across devices using your own local drive, Cloudflare R2, AWS S3, or Nextcloud/WebDAV.
- **❓ Contextual Help Screen**: Built-in keyboard shortcut reference and scoring mode guide available anywhere via `h` or `?`.
- **🖥️ Reactive TUI**: A responsive, modern terminal UI built with Textual.

## 📸 App in Action

![Netflix Narc TUI Mockup](./assets/screenshot.png)

## 🚀 Getting Started

### ⚡ Quick Start: Standalone Executable (Recommended — No Python Required!)

Download a pre-compiled standalone release from [GitHub Releases](https://github.com/Kilo59/netflix-narc/releases). No Python, `uv`, or setup required.

#### macOS & Linux (Archive — Recommended)
1. Download the archive for your architecture from the [Latest Release](https://github.com/Kilo59/netflix-narc/releases/latest):
   - **macOS (Apple Silicon M1/M2/M3/M4)**: `netflix-narc-aarch64-apple-darwin.tar.gz`
   - **macOS (Intel)**: `netflix-narc-x86_64-apple-darwin.tar.gz`
   - **Linux**: `netflix-narc-x86_64-unknown-linux-gnu.tar.gz`
2. Extract and launch:
   ```bash
   tar -xzf netflix-narc-aarch64-apple-darwin.tar.gz
   ./netflix-narc
   ```

> 💡 **Tip (Optional)**: Move `netflix-narc` to `/usr/local/bin/` so you can launch it from any directory:
> ```bash
> sudo mv netflix-narc /usr/local/bin/
> netflix-narc
> ```

*(Note: If you download the raw uncompressed binary file directly, run `chmod +x <binary-name>` once before executing).*

#### Windows
1. Download `netflix-narc-x86_64-pc-windows-msvc.zip` (or the raw `.exe`) from the [Latest Release](https://github.com/Kilo59/netflix-narc/releases/latest).
2. Extract the archive and launch from Command Prompt or PowerShell:
   ```powershell
   .\netflix-narc.exe
   ```


---

### 🐍 Alternative: Package Manager & Source Install (Requires Python 3.13+)

If you already have Python 3.13+ and prefer using a package manager:

#### Via `uv tool` (PyPI)

```bash
uv tool install netflix-narc
netflix-narc --help
```

#### Via `pipx` or `pip`

```bash
pipx install netflix-narc
# or
pip install netflix-narc
```

#### From GitHub Source

```bash
uv tool install git+https://github.com/Kilo59/netflix-narc
```

### Development Setup

1. Clone the repository and navigate into the `netflix-narc` directory.
2. Install dependencies with `uv sync`.
3. Run via `uv run netflix-narc`.


### Prerequisites & Setup
- Python 3.13+
- Your exported `NetflixViewingHistory.csv`
   *(Netflix Account Settings → Profile & Parental Controls → Viewing activity → Download all)*
- *(Optional)* An **OMDb API Key** — grab a free key at [omdbapi.com](https://www.omdbapi.com/apikey.aspx)

### Running the Application

```bash
# Point to your history file explicitly (recommended)
uv run netflix-narc --csv /path/to/NetflixViewingHistory.csv

# Or drop the file in the current directory as NetflixViewingHistory.csv and run
uv run netflix-narc
```

On first launch, Netflix Narc automatically starts the **Onboarding Wizard** to configure child age targets and content weightings. At any time, press `s` to open **Preferences** or `h` / `?` for **Help**.

### ☁️ Storage & Multi-Device Sync (BYOS)

Netflix Narc operates **100% local-first** with zero central tracking. If you want to synchronize your Evidence Locker dossiers and preference settings across multiple computers, you can enable **Bring-Your-Own-Storage (BYOS)**:

#### 1. Setup via TUI (Recommended)
1. Press `s` in the app to open **Preferences & Storage Configuration**.
2. Select your preferred **Sync Storage Backend** from the dropdown.
3. Fill in your credentials/paths and click **Test Connection**.
4. Click **Save Settings** to persist your setup.

#### 2. Setup via Environment Variables (`~/.config/netflix-narc/.env`)

You can also configure sync directly in your environment or `~/.config/netflix-narc/.env`:

- **Local Folder / Cloud Drive** (iCloud Drive, Dropbox, Syncthing, shared network drive):
  ```env
  SYNC_BACKEND=local_folder
  SYNC_LOCAL_PATH=/Users/username/Library/Mobile Documents/com~apple~CloudDocs/netflix-narc-sync
  ```

- **S3-Compatible Object Storage** (Cloudflare R2, AWS S3, MinIO, Wasabi):
  ```env
  SYNC_BACKEND=s3
  SYNC_S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
  SYNC_S3_BUCKET=my-narc-bucket
  SYNC_S3_ACCESS_KEY_ID=your_access_key_id
  SYNC_S3_SECRET_ACCESS_KEY=your_secret_access_key
  ```

- **WebDAV / Nextcloud / ownCloud**:
  ```env
  SYNC_BACKEND=webdav
  SYNC_WEBDAV_URL=https://nextcloud.example.com/remote.php/dav/files/username/netflix-narc
  SYNC_WEBDAV_USERNAME=your_username
  SYNC_WEBDAV_PASSWORD=your_app_password
  ```

### ⌨️ Keybindings

- `l`: Open **The Lineup** (priority review queue)
- `i`: Open **Interrogation Room** (manual data entry for selected title)
- `s`: Open **Preferences** (settings, weights, API provider & BYOS sync)
- `a`: Open **Advanced Options** (Load CSV, Evaluate API)
- `h` / `?`: Contextual **Help Overlay**
- `Enter`: Expand/Collapse show episodes and suitability sub-bars
- `q`: Quit Application

## 📜 How it Works
1. You provide your Netflix viewing history CSV.
2. The Onboarding Wizard aligns your target child age and content sensitivity thresholds.
3. Netflix Narc cross-references titles against API metadata or your local Evidence Locker.
4. Use **The Lineup** (`l`) and **Interrogation Room** (`i`) to manually score missing or unrated titles.
5. Expand any row in the main table to inspect granular suitability sub-bars and exact violation flags.

---

*Built with ❤️ (and a healthy dose of parental suspicion) using Python and Textual.*
