import functools
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap

from packaging import version

import pytest


NATIVE_TOXENV = f"py{sys.version_info[0]}{sys.version_info[1]}"
NATIVE_EXECUTABLE = str(pathlib.Path(sys.executable).resolve())
NATIVE_EXEC_PREFIX = str(pathlib.Path(sys.exec_prefix).resolve())
NATIVE_EXEC_PREFIX_MSG = f"{NATIVE_EXEC_PREFIX} is the exec_prefix"
FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
DOT_TOX = pathlib.Path("./.tox")


@pytest.fixture(autouse=True)
def projdir(tmp_path, monkeypatch):
    pwd = tmp_path / "projdir"
    pwd.mkdir()
    for fname in "tox.ini", "setup.py":
        shutil.copy(FIXTURES_DIR / fname, pwd)
    monkeypatch.chdir(pwd)


def tox(*args, **kwargs):
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("stderr", subprocess.PIPE)
    kwargs.setdefault("check", True)
    cp = subprocess.run((sys.executable, "-m", "tox", "-q") + args, **kwargs)
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


TOX_VERSION = version.parse(tox("--version").stdout.split(" ")[0])
TOX313 = TOX_VERSION < version.parse("3.14")


needs_py36789 = pytest.mark.skipif(
    not all((is_available(f"python3.{x}") for x in range(6, 10))),
    reason="This test needs python3.6, 3.7, 3.8 and 3.9 available in $PATH",
)



def test_native_toxenv_current_env():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG
    assert not (DOT_TOX / NATIVE_TOXENV / "lib").is_dir()


@needs_py36789
def test_all_toxenv_current_env():
    result = tox("--current-env", check=False)
    assert NATIVE_EXEC_PREFIX_MSG in result.stdout.splitlines()
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


@needs_py36789
def test_all_toxenv_current_env_skip_missing():
    result = tox("--current-env", "--skip-missing-interpreters", check=False)
    assert "InterpreterMismatch:" in result.stdout
    assert "congratulations" in result.stdout
    assert result.returncode == 0


@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38", "py39"])
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
        six
        py
        ___________________________________ summary ____________________________________
          py36: commands succeeded
          py37: commands succeeded
          py38: commands succeeded
          py39: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38", "py39"])
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
    assert depspath.read_text().splitlines() == ["six", "py"] * 4
    expected = textwrap.dedent(
        """
        ___________________________________ summary ____________________________________
          py36: commands succeeded
          py37: commands succeeded
          py38: commands succeeded
          py39: commands succeeded
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


@needs_py36789
def test_regular_run():
    result = tox()
    lines = sorted(result.stdout.splitlines()[:4])
    assert "/.tox/py36 is the exec_prefix" in lines[0]
    assert "/.tox/py37 is the exec_prefix" in lines[1]
    assert "/.tox/py38 is the exec_prefix" in lines[2]
    assert "/.tox/py39 is the exec_prefix" in lines[3]
    assert "congratulations" in result.stdout
    for y in 6, 7, 8, 9:
        if TOX313 and y > 8:
            # there is a bug in tox < 3.14,
            # it creates venv with /usr/bin/python3 if the version is unknown
            # See https://src.fedoraproject.org/rpms/python-tox/pull-request/15
            continue
        for pkg in "py", "six", "test":
            sitelib = DOT_TOX / f"py3{y}/lib/python3.{y}/site-packages"
            assert sitelib.is_dir()
            assert len(list(sitelib.glob(f"{pkg}-*.dist-info"))) == 1


def test_regular_run_native_toxenv():
    result = tox("-e", NATIVE_TOXENV)
    lines = sorted(result.stdout.splitlines()[:1])
    assert f"/.tox/{NATIVE_TOXENV} is the exec_prefix" in lines[0]
    assert "congratulations" in result.stdout
    for pkg in "py", "six", "test":
        sitelib = (
            DOT_TOX / f"{NATIVE_TOXENV}/lib/python3.{NATIVE_TOXENV[-1]}/site-packages"
        )
        assert sitelib.is_dir()
        assert len(list(sitelib.glob(f"{pkg}-*.dist-info"))) == 1


def test_regular_after_current_is_supported():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG
    result = tox("-e", NATIVE_TOXENV)
    assert f"/.tox/{NATIVE_TOXENV} is the exec_prefix" in result.stdout
    assert "--recreate" not in result.stderr


def test_regular_after_killed_current_is_not_supported():
    # fake broken tox run
    shutil.rmtree(DOT_TOX, ignore_errors=True)
    (DOT_TOX / NATIVE_TOXENV / "bin").mkdir(parents=True)
    (DOT_TOX / NATIVE_TOXENV / "bin" / "python").symlink_to(NATIVE_EXECUTABLE)

    result = tox("-e", NATIVE_TOXENV, check=False)
    assert result.returncode > 0
    assert "--recreate" in result.stderr


def test_regular_after_first_deps_only_is_supported():
    result = tox("-e", NATIVE_TOXENV, "--print-deps-only")
    assert result.stdout.splitlines()[0] == "six"
    result = tox("-e", NATIVE_TOXENV)
    lines = sorted(result.stdout.splitlines()[:1])
    assert "--recreate" not in result.stderr
    assert f"/.tox/{NATIVE_TOXENV} is the exec_prefix" in lines[0]

    # check that "test" was not installed to current environment
    shutil.rmtree("./test.egg-info")
    pip_freeze = subprocess.run(
        (sys.executable, "-m", "pip", "freeze"),
        encoding="utf-8",
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    # XXX when this fails, recreate your current environment
    assert "test==0.0.0" not in pip_freeze


def test_regular_recreate_after_current():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG
    result = tox("-re", NATIVE_TOXENV)
    assert f"/.tox/{NATIVE_TOXENV} is the exec_prefix" in result.stdout
    assert "not supported" not in result.stderr
    assert "--recreate" not in result.stderr


def test_current_after_regular_is_not_supported():
    result = tox("-e", NATIVE_TOXENV)
    assert f"/.tox/{NATIVE_TOXENV} is the exec_prefix" in result.stdout
    result = tox("-e", NATIVE_TOXENV, "--current-env", check=False)
    assert result.returncode > 0
    assert "not supported" in result.stderr


def test_current_recreate_after_regular():
    result = tox("-e", NATIVE_TOXENV)
    assert f"/.tox/{NATIVE_TOXENV} is the exec_prefix" in result.stdout
    result = tox("-re", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG


def test_current_after_deps_only():
    # this is quite fast, so we can do it several times
    for _ in range(3):
        result = tox("-e", NATIVE_TOXENV, "--print-deps-only")
        assert "bin/python" not in result.stdout
        assert "six" in result.stdout
        result = tox("-re", NATIVE_TOXENV, "--current-env")
        assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG


def test_regular_recreate_after_deps_only():
    result = tox("-e", NATIVE_TOXENV, "--print-deps-only")
    assert "bin/python" not in result.stdout
    assert "six" in result.stdout

    result = tox("-re", NATIVE_TOXENV)
    assert result.stdout.splitlines()[0] != NATIVE_EXEC_PREFIX_MSG
    sitelib = DOT_TOX / f"{NATIVE_TOXENV}/lib/python3.{NATIVE_TOXENV[-1]}/site-packages"
    assert sitelib.is_dir()
    assert len(list(sitelib.glob("test-*.dist-info"))) == 1

    result = tox("-e", NATIVE_TOXENV, "--print-deps-only")
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
