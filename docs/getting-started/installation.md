# Installation Guide

Learn how to install **netflix-narc** on your system.

## Option A: Standalone Binary (Recommended)

Download the latest executable for your platform from [GitHub Releases](https://github.com/Kilo59/netflix-narc/releases).

### macOS
```bash
xattr -d com.apple.quarantine netflix-narc
chmod +x netflix-narc
./netflix-narc
```

## Option B: Package Manager

Install via `uv` or `pip`:

```bash
uv tool install netflix-narc
# or
pip install netflix-narc
```
