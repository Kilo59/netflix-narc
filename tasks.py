"""Task runner for development tasks."""

from __future__ import annotations

import os
import pathlib
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
    print(ver)  # noqa: T201
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
def test(ctx: Context, *, coverage: bool = False) -> None:  # noqa: PT028
    """Run tests with pytest."""
    cmds = ["pytest", "-vv"]
    if coverage:
        cmds.extend(["--cov=netflix_narc", "--cov-report=term-missing"])
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
    print(f"Building PyApp binary for wheel: {latest_wheel}")  # noqa: T201

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
        print(f"Ad-hoc code signing binary for macOS: {target_bin}")  # noqa: T201
        ctx.run(f"codesign --force --deep -s - {target_bin}", echo=True, pty=USE_PTY)

    if archive and target_bin.exists():
        tarball_path = dist_dir / "netflix-narc.tar.gz"
        print(f"Archiving binary to: {tarball_path}")  # noqa: T201
        ctx.run(f"tar -czf {tarball_path} -C {dist_dir} netflix-narc", echo=True, pty=USE_PTY)
