import os
import pathlib
import shutil
import subprocess
import sys
import textwrap

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
    assert not (DOT_TOX / NATIVE_TOXENV / "lib").is_dir()


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


@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38"])
def test_print_deps_only(toxenv):
    result = tox("-e", toxenv, "--print-deps-only")
    expected = textwrap.dedent(
        f"""
        six
        py
        ___________________________________ summary ____________________________________
          {toxenv}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


def test_allenvs_print_deps_only():
    result = tox("--print-deps-only")
    expected = textwrap.dedent(
        """
        six
        py
        six
        py
        six
        py
        ___________________________________ summary ____________________________________
          py36: commands succeeded
          py37: commands succeeded
          py38: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


def test_regular_run():
    result = tox()
    lines = sorted(result.stdout.splitlines()[:3])
    assert "/.tox/py36/bin/python" in lines[0]
    assert "/.tox/py37/bin/python" in lines[1]
    assert "/.tox/py38/bin/python" in lines[2]
    assert "congratulations" in result.stdout
    for y in 6, 7, 8:
        for pkg in "py", "six", "test":
            sitelib = DOT_TOX / f"py3{y}/lib/python3.{y}/site-packages"
            assert sitelib.is_dir()
            assert len(list(sitelib.glob(f"{pkg}-*.dist-info"))) == 1


def test_regular_after_current_is_not_supported():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXECUTABLE
    result = tox("-e", NATIVE_TOXENV, prune=False, check=False)
    assert result.returncode > 0
    assert "not supported" in result.stderr


def test_regular_recreate_after_current():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXECUTABLE
    result = tox("-re", NATIVE_TOXENV, prune=False)
    assert f"/.tox/{NATIVE_TOXENV}/bin/python" in result.stdout
    assert "not supported" not in result.stderr


def test_current_after_regular_is_not_supported():
    result = tox("-e", NATIVE_TOXENV)
    assert f"/.tox/{NATIVE_TOXENV}/bin/python" in result.stdout
    result = tox("-e", NATIVE_TOXENV, "--current-env", prune=False, check=False)
    assert result.returncode > 0
    assert "not supported" in result.stderr


def test_current_recreate_after_regular():
    result = tox("-e", NATIVE_TOXENV)
    assert f"/.tox/{NATIVE_TOXENV}/bin/python" in result.stdout
    result = tox("-re", NATIVE_TOXENV, "--current-env", prune=False)
    assert result.stdout.splitlines()[0] == NATIVE_EXECUTABLE


def test_current_after_deps_only():
    # this is quite fast, so we can do it several times
    first = True
    for _ in range(3):
        result = tox("-e", NATIVE_TOXENV, "--print-deps-only", prune=first)
        first = False
        assert "bin/python" not in result.stdout
        assert "six" in result.stdout
        result = tox("-re", NATIVE_TOXENV, "--current-env", prune=False)
        assert result.stdout.splitlines()[0] == NATIVE_EXECUTABLE


def test_regular_after_deps_only():
    result = tox("-e", NATIVE_TOXENV, "--print-deps-only")
    assert "bin/python" not in result.stdout
    assert "six" in result.stdout

    result = tox("-re", NATIVE_TOXENV, prune=False)
    assert result.stdout.splitlines()[0] != NATIVE_EXECUTABLE

    result = tox("-e", NATIVE_TOXENV, "--print-deps-only", prune=False)
    assert "bin/python" not in result.stdout
    assert "six" in result.stdout
