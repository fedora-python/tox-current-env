import os
import shutil

import pytest
from utils import FIXTURES_DIR, TOX_VERSION, TOX4, modify_config, drop_unsupported_pythons


@pytest.fixture(autouse=True)
def projdir(tmp_path, monkeypatch, worker_id):
    pwd = tmp_path / "projdir"
    pwd.mkdir()
    for fname in "tox.ini", "setup.py", "pyproject.toml":
        shutil.copy(FIXTURES_DIR / fname, pwd)
    if TOX4:
        with modify_config(pwd / "tox.ini") as config:
            config["tox"]["envlist"] = drop_unsupported_pythons(config["tox"]["envlist"])
    monkeypatch.chdir(pwd)
    # https://github.com/pypa/pip/issues/5345#issuecomment-386424455
    monkeypatch.setenv("XDG_CACHE_HOME",
                       os.path.expanduser(f"~/.cache/pytest-xdist-{worker_id}"))
    return pwd


if TOX4:
    available_options = ("--print-deps-to-file=-", "--print-deps-to=-")
else:
    available_options = (
        "--print-deps-only",
        "--print-deps-to-file=-",
        "--print-deps-to=-",
    )


@pytest.fixture(params=available_options)
def print_deps_stdout_arg(request):
    """Argument for printing deps to stdout"""
    return request.param


@pytest.fixture(params=("--print-extras-to-file=-", "--print-extras-to=-"))
def print_extras_stdout_arg(request):
    """Argument for printing extras to stdout"""
    return request.param


@pytest.fixture
def dependency_groups_support():
    """Support for dependency groups"""
    if (TOX_VERSION.major, TOX_VERSION.minor) < (4, 22):
        raise pytest.skip(reason="requires tox 4.22 or higher")


@pytest.fixture(params=("--print-dependency-groups-to-file=-", "--print-dependency-groups-to=-"))
def print_dependency_groups_stdout_arg(request, dependency_groups_support):
    """Argument for printing dependency groups to stdout"""
    return request.param
