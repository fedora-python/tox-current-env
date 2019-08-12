import functools
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


@functools.lru_cache(maxsize=8)
def is_available(python):
    try:
        subprocess.run((python, "--version"))
    except FileNotFoundError:
        return False
    return True


needs_py3678 = pytest.mark.skipif(
    not is_available("python3.6")
    or not is_available("python3.7")
    or not is_available("python3.8"),
    reason="This test needs all of python3.6, python3.7 and python3.8 to be available in $PATH",
)


def test_native_toxenv_current_env():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXECUTABLE
    assert not (DOT_TOX / NATIVE_TOXENV / "lib").is_dir()


@needs_py3678
def test_all_toxenv_current_env():
    result = tox("--current-env", check=False)
    assert NATIVE_EXECUTABLE in result.stdout.splitlines()
    assert result.stdout.count("InterpreterMismatch:") >= 2
    assert result.returncode > 0


@pytest.mark.parametrize("python", ["python3.4", "python3.5"])
def test_missing_toxenv_current_env(python):
    if is_available(python):
        pytest.skip(f"Only works if {python} is not available in $PATH")
    env = python.replace("python", "py").replace(".", "")
    result = tox("-e", env, "--current-env", check=False)
    assert f"InterpreterNotFound: {python}" in result.stdout
    assert "Traceback" not in (result.stderr + result.stdout)
    assert result.returncode > 0


@needs_py3678
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


@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38"])
def test_print_deps_to_file(toxenv, tmp_path):
    depspath = tmp_path / "deps"
    result = tox("-e", toxenv, "--print-deps-to-file", str(depspath))
    assert depspath.read_text().splitlines() == ["six", "py"]
    expected = textwrap.dedent(
        f"""
        ___________________________________ summary ____________________________________
          {toxenv}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


def test_allenvs_print_deps_to_file(tmp_path):
    depspath = tmp_path / "deps"
    result = tox("--print-deps-to-file", str(depspath))
    assert depspath.read_text().splitlines() == ["six", "py"] * 3
    expected = textwrap.dedent(
        """
        ___________________________________ summary ____________________________________
          py36: commands succeeded
          py37: commands succeeded
          py38: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


def test_allenvs_print_deps_to_existing_file(tmp_path):
    depspath = tmp_path / "deps"
    depspath.write_text("nada")
    result = tox("--print-deps-to-file", str(depspath))
    lines = depspath.read_text().splitlines()
    assert "nada" not in lines
    assert "six" in lines
    assert "py" in lines


def test_print_deps_only_print_deps_to_file_are_mutually_exclusive():
    result = tox(
        "-e",
        NATIVE_TOXENV,
        "--print-deps-only",
        "--print-deps-to-file",
        "foobar",
        check=False,
    )
    assert result.returncode > 0
    assert "cannot be used together" in result.stderr


@needs_py3678
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


def test_regular_run_native_toxenv():
    result = tox("-e", NATIVE_TOXENV)
    lines = sorted(result.stdout.splitlines()[:1])
    assert f"/.tox/{NATIVE_TOXENV}/bin/python" in lines[0]
    assert "congratulations" in result.stdout
    for pkg in "py", "six", "test":
        sitelib = (
            DOT_TOX / f"{NATIVE_TOXENV}/lib/python3.{NATIVE_TOXENV[-1]}/site-packages"
        )
        assert sitelib.is_dir()
        assert len(list(sitelib.glob(f"{pkg}-*.dist-info"))) == 1


def test_regular_after_current_is_not_supported():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXECUTABLE
    result = tox("-e", NATIVE_TOXENV, prune=False, check=False)
    assert result.returncode > 0
    assert "not supported" in result.stderr


def test_regular_after_first_deps_only_is_not_supported():
    result = tox("-e", NATIVE_TOXENV, "--print-deps-only")
    assert result.stdout.splitlines()[0] == "six"
    result = tox("-e", NATIVE_TOXENV, prune=False, check=False)
    assert result.returncode > 0
    assert "not supported" in result.stderr

    # check that "test" was not installed to current environment
    pip_freeze = subprocess.run(
        (sys.executable, "-m", "pip", "freeze"),
        encoding="utf-8",
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    assert "test==0.0.0" not in pip_freeze


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


def test_regular_recreate_after_deps_only():
    result = tox("-e", NATIVE_TOXENV, "--print-deps-only")
    assert "bin/python" not in result.stdout
    assert "six" in result.stdout

    result = tox("-re", NATIVE_TOXENV, prune=False)
    assert result.stdout.splitlines()[0] != NATIVE_EXECUTABLE
    sitelib = DOT_TOX / f"{NATIVE_TOXENV}/lib/python3.{NATIVE_TOXENV[-1]}/site-packages"
    assert sitelib.is_dir()
    assert len(list(sitelib.glob("test-*.dist-info"))) == 1

    result = tox("-e", NATIVE_TOXENV, "--print-deps-only", prune=False)
    assert "bin/python" not in result.stdout
    assert "six" in result.stdout


def test_print_deps_without_python_command(tmp_path):
    bin = tmp_path / "bin"
    bin.mkdir()
    tox_link = bin / "tox"
    tox_path = shutil.which("tox")
    tox_link.symlink_to(tox_path)
    env = {**os.environ, "PATH": str(bin)}

    result = tox("-e", NATIVE_TOXENV, "--print-deps-only", env=env)
    expected = textwrap.dedent(
        f"""
        six
        py
        ___________________________________ summary ____________________________________
          {NATIVE_TOXENV}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected
