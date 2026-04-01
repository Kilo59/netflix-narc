"""Task runner for development tasks."""

from __future__ import annotations

import pathlib

from invoke import Context, task  # type: ignore[attr-defined]

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
    cmds = ["mypy", "."]
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
