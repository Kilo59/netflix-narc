"""Task runner for development tasks."""

from __future__ import annotations

import os
import pathlib
import shlex
import shutil
import sys
import tomllib
from typing import TYPE_CHECKING

from invoke.tasks import task

if TYPE_CHECKING:
    from invoke.context import Context

# Project constants
PROJECT_NAME = "netflix-narc"
PYPROJECT_TOML = pathlib.Path("pyproject.toml")
DEFAULT_PYAPP_VERSION = "0.24.0"
PYAPP_VERSION = os.getenv("PYAPP_VERSION", DEFAULT_PYAPP_VERSION)
USE_PTY = sys.platform != "win32"


@task(
    aliases=["version"],
)
def get_project_version(ctx: Context) -> str:  # noqa: ARG001
    """Print and return the project version from pyproject.toml."""
    with PYPROJECT_TOML.open("rb") as f:
        data = tomllib.load(f)
    ver: str = data["project"]["version"]
    print(ver)
    return ver


@task
def fmt(ctx: Context, *, check: bool = False) -> None:
    """Format code with ruff format."""
    cmds = ["ruff", "format", "."]
    if check:
        cmds.append("--check")
    ctx.run(" ".join(cmds), echo=True, pty=USE_PTY)


@task(
    help={
        "check": "Check code without fixing it",
        "unsafe_fixes": "Apply 'un-safe' fixes. See https://docs.astral.sh/ruff/linter/#fix-safety",
    }
)
def lint(ctx: Context, *, check: bool = False, unsafe_fixes: bool = False) -> None:
    """Lint and fix code with ruff."""
    cmds = ["ruff", "check", "."]
    if not check:
        cmds.append("--fix")
    if unsafe_fixes:
        cmds.extend(["--unsafe-fixes", "--show-fixes"])
    ctx.run(" ".join(cmds), echo=True, pty=USE_PTY)


@task(
    aliases=["types"],
)
def type_check(ctx: Context, *, install_types: bool = False, check: bool = False) -> None:
    """Type check code with mypy."""
    cmds = ["mypy"]
    if install_types:
        cmds.append("--install-types")
    if check:
        cmds.extend(["--pretty"])
    ctx.run(" ".join(cmds), echo=True, pty=USE_PTY)


@task
def test(ctx: Context, *, coverage: bool = False, junit: bool = False) -> None:
    """Run tests with pytest."""
    cmds = ["pytest", "-vv"]
    if coverage:
        cmds.extend(["--cov=netflix_narc", "--cov-report=term-missing", "--cov-report=xml"])
    if junit:
        cmds.extend(["--junitxml=junit.xml", "-o", "junit_family=legacy"])
    ctx.run(" ".join(cmds), echo=True, pty=USE_PTY)


@task
def deps(ctx: Context) -> None:
    """Sync dependencies with uv lock file."""
    ctx.run("uv sync", echo=True, pty=USE_PTY)


@task(
    help={
        "embed": "Embed CPython runtime and wheel directly into binary for offline execution",
        "archive": "Create a .tar.gz / .zip archive alongside raw binary",
    }
)
def build_binary(ctx: Context, *, embed: bool = True, archive: bool = True) -> None:
    """Build a standalone single-file binary using PyApp."""
    ctx.run("uv build --wheel", echo=True, pty=USE_PTY)
    dist_dir = pathlib.Path("dist")
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        msg = "No wheel found in dist/ directory after build."
        raise RuntimeError(msg)
    latest_wheel = max(wheels, key=lambda p: p.stat().st_mtime)
    print(f"Building PyApp binary for wheel: {latest_wheel}")

    env = {
        "PYAPP_PROJECT_NAME": "netflix-narc",
        "PYAPP_PROJECT_VERSION": get_project_version(ctx),
        "PYAPP_EXEC_SPEC": "netflix_narc.main:main",
        "PYAPP_PYTHON_VERSION": "3.13",
        "PYAPP_WHEEL_FILE": str(latest_wheel.resolve()),
    }

    if embed:
        env["PYAPP_EMBED"] = "1"

    # NOTE(maintainers): PyApp bakes project metadata and wheel binaries into the executable
    # at compile time via Rust's build.rs (`PYAPP_EMBED=1`). Therefore, a generic pre-compiled
    # binary (e.g. via cargo-binstall) cannot be used. We specify `--version` and `--locked` to
    # pin the exact PyApp crate and force Cargo to use PyApp's upstream Cargo.lock for 100%
    # deterministic builds. PYAPP_VERSION can be overridden via environment variable if needed.
    bin_dir = dist_dir / "bin"
    ctx.run(
        f"cargo install pyapp --version {PYAPP_VERSION} --locked --root {bin_dir}",
        echo=True,
        pty=USE_PTY,
        env=env,
    )

    compiled_bin = bin_dir / "bin" / "pyapp"
    if not compiled_bin.exists():
        compiled_bin = bin_dir / "bin" / "pyapp.exe"

    target_bin = dist_dir / "netflix-narc"
    shutil.copy(compiled_bin, target_bin)
    target_bin.chmod(0o755)

    if sys.platform == "darwin":
        print(f"Ad-hoc code signing binary for macOS: {target_bin}")
        ctx.run(
            f"codesign --force --deep -s - {shlex.quote(str(target_bin))}",
            echo=True,
            pty=USE_PTY,
        )

    if archive and target_bin.exists():
        tarball_path = dist_dir / "netflix-narc.tar.gz"
        print(f"Archiving binary to: {tarball_path}")
        ctx.run(f"tar -czf {tarball_path} -C {dist_dir} netflix-narc", echo=True, pty=USE_PTY)


@task(
    aliases=["docs"],
    help={
        "host": "Host interface to bind (default: 127.0.0.1)",
        "port": "Port to bind (default: 8000)",
    },
)
def docs_serve(ctx: Context, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Serve documentation locally using Zensical."""
    ctx.run(f"uv run --group docs zensical serve -a {host}:{port}", echo=True, pty=USE_PTY)


@task
def docs_build(ctx: Context) -> None:
    """Build documentation static site using Zensical."""
    ctx.run("uv run --group docs zensical build", echo=True, pty=USE_PTY)


@task(
    aliases=["screenshots"],
    help={
        "output_dir": "Directory where generated SVG screenshots will be saved",
        "csv_path": "Path to Netflix viewing history CSV file",
    },
)
def docs_screenshots(
    ctx: Context, output_dir: str | None = None, csv_path: str | None = None
) -> None:
    """Generate SVG TUI screenshots for documentation using Textual export."""
    cmd = ["uv", "run", "python", "scripts/generate_tui_screenshots.py"]
    if output_dir:
        cmd.extend(["--output-dir", shlex.quote(output_dir)])
    if csv_path:
        cmd.extend(["--csv-path", shlex.quote(csv_path)])
    ctx.run(" ".join(cmd), echo=True, pty=USE_PTY)


@task(
    help={
        "tape": "Specific tape script name (without .tape extension) to run",
    }
)
def recordings(ctx: Context, tape: str | None = None) -> None:
    """Regenerate CLI animation GIFs using Charm VHS tape scripts."""
    if tape:
        ctx.run(f"vhs tapes/{tape}.tape", echo=True, pty=USE_PTY)
    else:
        ctx.run("vhs tapes/*.tape", echo=True, pty=USE_PTY)
