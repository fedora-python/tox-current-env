import os
import pathlib
import shutil
import subprocess
import sys

import pytest


NATIVE_TOXENV = f"py{sys.version_info[0]}{sys.version_info[1]}"
NATIVE_EXECUTABLE = str(pathlib.Path(sys.executable).resolve())
TOX_INI = pathlib.Path(__file__).parent / "tox.ini"
DOT_TOX = pathlib.Path(__file__).parent / ".tox"


def tox(*args, prune=True, **kwargs):
    if prune:
        shutil.rmtree(DOT_TOX, ignore_errors=True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("stderr", subprocess.PIPE)
    kwargs.setdefault("check", True)
    cp = subprocess.run((sys.executable, "-m", "tox", "-qc", TOX_INI) + args, **kwargs)
    print(cp.stdout, file=sys.stdout)
    print(cp.stderr, file=sys.stderr)
    return cp


def test_native_toxenv_current_env():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXECUTABLE


def test_all_toxenv_current_env():
    result = tox("--current-env", check=False)
    assert NATIVE_EXECUTABLE in result.stdout.splitlines()
    assert result.stdout.count("InterpreterMismatch:") >= 2
    assert result.returncode > 0


def test_all_toxenv_current_env_skip_missing():
    result = tox("--current-env", "--skip-missing-interpreters", check=False)
    assert "InterpreterMismatch:" in result.stdout
    assert "congratulations" in result.stdout
    assert result.returncode == 0


def test_native_toxenv_print_deps_only():
    result = tox("-e", NATIVE_TOXENV, "--print-deps-only")
    assert result.stdout.splitlines()[0] == "six"
    assert result.stdout.splitlines()[1] == "py"


def test_regular_run():
    result = tox()
    lines = sorted(result.stdout.splitlines()[:3])
    assert "/.tox/py36/bin/python" in lines[0]
    assert "/.tox/py37/bin/python" in lines[1]
    assert "/.tox/py38/bin/python" in lines[2]
    assert "congratulations" in result.stdout


def test_regular_after_current():
    tox("-e", NATIVE_TOXENV, "--current-env")
    result = tox("-e", NATIVE_TOXENV, prune=False)
    assert f"/.tox/{NATIVE_TOXENV}/bin/python" in result.stdout.splitlines()[0]


@pytest.mark.xfail(reason="Regular tox refuses to remove our fake virtualenv")
def test_regular_recreate_after_current():
    tox("-e", NATIVE_TOXENV, "--current-env")
    tox("-re", NATIVE_TOXENV, prune=False)


def test_current_after_regular():
    tox("-e", NATIVE_TOXENV)
    tox("-e", NATIVE_TOXENV, "--current-env", prune=False)
