"""Task runner for development tasks."""

from __future__ import annotations

import pathlib
import shutil
from typing import TYPE_CHECKING

from invoke.tasks import task

if TYPE_CHECKING:
    from invoke.context import Context

# Project constants
PROJECT_NAME = "netflix-narc"
PYPROJECT_TOML = pathlib.Path("pyproject.toml")


@task
def fmt(ctx: Context, *, check: bool = False) -> None:
    """Format code with ruff format."""
    cmds = ["ruff", "format", "."]
    if check:
        cmds.append("--check")
    ctx.run(" ".join(cmds), echo=True, pty=True)


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
    ctx.run(" ".join(cmds), echo=True, pty=True)


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
    ctx.run(" ".join(cmds), echo=True, pty=True)


@task
def test(ctx: Context, *, coverage: bool = False) -> None:  # noqa: PT028
    """Run tests with pytest."""
    cmds = ["pytest", "-vv"]
    if coverage:
        cmds.extend(["--cov=netflix_narc", "--cov-report=term-missing"])
    ctx.run(" ".join(cmds), echo=True, pty=True)


@task
def deps(ctx: Context) -> None:
    """Sync dependencies with uv lock file."""
    ctx.run("uv sync", echo=True, pty=True)


@task(
    help={
        "embed": "Embed CPython runtime and wheel directly into binary for offline execution",
        "archive": "Create a .tar.gz / .zip archive alongside raw binary",
    }
)
def build_binary(ctx: Context, *, embed: bool = True, archive: bool = True) -> None:
    """Build a standalone single-file binary using PyApp."""
    ctx.run("uv build --wheel", echo=True, pty=True)
    dist_dir = pathlib.Path("dist")
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        msg = "No wheel found in dist/ directory after build."
        raise RuntimeError(msg)
    latest_wheel = max(wheels, key=lambda p: p.stat().st_mtime)
    print(f"Building PyApp binary for wheel: {latest_wheel}")  # noqa: T201
    env = {"PYAPP_EMBED": "1"} if embed else None
    if not shutil.which("pyapp"):
        print("pyapp CLI not found in PATH. Installing via cargo install pyapp...")  # noqa: T201
        ctx.run("cargo install pyapp", echo=True, pty=True)
    ctx.run(f"pyapp build {latest_wheel}", echo=True, pty=True, env=env)

    # Set executable permissions on unix platforms
    binary_path = dist_dir / "netflix-narc"
    if binary_path.exists():
        binary_path.chmod(0o755)

    if archive and binary_path.exists():
        tarball_path = dist_dir / "netflix-narc.tar.gz"
        print(f"Archiving binary to: {tarball_path}")  # noqa: T201
        ctx.run(f"tar -czf {tarball_path} -C {dist_dir} netflix-narc", echo=True, pty=True)
