import os
import shutil

import pytest
from utils import FIXTURES_DIR, TOX4


@pytest.fixture(autouse=True)
def projdir(tmp_path, monkeypatch, worker_id):
    pwd = tmp_path / "projdir"
    pwd.mkdir()
    for fname in "tox.ini", "setup.py":
        shutil.copy(FIXTURES_DIR / fname, pwd)
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
