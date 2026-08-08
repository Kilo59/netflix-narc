"""Distribution smoke tests to verify wheel packaging and isolated execution."""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import pytest


@pytest.mark.slow
def test_wheel_distribution_smoke_test(tmp_path: pathlib.Path) -> None:
    """Build wheel, install into isolated venv, run CLI from outside repo root.

    This ensures narc.tcss and all required static assets are bundled in the wheel
    and that CWD isolation does not hide missing package data.
    """
    repo_root = pathlib.Path(__file__).parent.parent
    dist_dir = tmp_path / "dist"
    venv_dir = tmp_path / "venv"

    uv_path = shutil.which("uv")
    assert uv_path is not None, "uv binary must be present on PATH to run distribution test"

    # 1. Build wheel into isolated dist_dir using uv build
    build_res = subprocess.run(
        [uv_path, "build", "--wheel", "--out-dir", str(dist_dir), str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_res.returncode == 0, f"uv build failed:\n{build_res.stderr}"

    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, f"Expected 1 wheel in {dist_dir}, found {wheels}"
    wheel_path = wheels[0]

    # 2. Create isolated venv using venv module
    venv_res = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert venv_res.returncode == 0, f"venv creation failed:\n{venv_res.stderr}"

    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    # 3. Install wheel and dependencies into isolated venv
    install_res = subprocess.run(
        [uv_path, "pip", "install", "--python", str(venv_python), str(wheel_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert install_res.returncode == 0, f"uv pip install failed:\n{install_res.stderr}"

    # 4. Verify narc.tcss exists inside the installed package in site-packages
    site_packages_dirs = list(venv_dir.glob("**/site-packages/netflix_narc"))
    assert len(site_packages_dirs) == 1, (
        f"Could not find installed package directory in venv: {venv_dir}"
    )
    tcss_file = site_packages_dirs[0] / "narc.tcss"
    assert tcss_file.exists(), f"narc.tcss is missing from installed package: {tcss_file}"

    # 5. Execute import, app initialization, and default CSS loading from isolated CWD
    isolated_cwd = tmp_path / "isolated_cwd"
    isolated_cwd.mkdir()

    check_code = (
        "import pathlib, netflix_narc.main, netflix_narc.settings; "
        "st = netflix_narc.settings.Settings(_env_file=None); "
        "app = netflix_narc.main.NetflixNarcApp(settings=st); "
        "css_sources = list(app._get_default_css()); "
        "assert len(css_sources) > 0, 'No default CSS sources loaded'; "
        "p = pathlib.Path(netflix_narc.main.__file__).parent / 'narc.tcss'; "
        "assert p.exists(), f'{p} missing'; "
        "assert p.read_text(encoding='utf-8').strip(), f'{p} empty'"
    )
    res = subprocess.run(
        [str(venv_python), "-c", check_code],
        cwd=isolated_cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    err_msg = (
        f"Distribution smoke test failed in isolated CWD!\n"
        f"stdout: {res.stdout}\n"
        f"stderr: {res.stderr}"
    )
    assert res.returncode == 0, err_msg


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
