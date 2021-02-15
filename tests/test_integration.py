import functools
import os
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap
import warnings
import configparser
import contextlib

from packaging.version import parse as ver

import pytest


NATIVE_TOXENV = f"py{sys.version_info[0]}{sys.version_info[1]}"
NATIVE_EXECUTABLE = str(pathlib.Path(sys.executable).resolve())
FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
DOT_TOX = pathlib.Path("./.tox")


def _exec_prefix(executable):
    """Returns sys.exec_prefix for the given executable"""
    cmd = (executable, "-c", "import sys; print(sys.exec_prefix)")
    return subprocess.check_output(cmd, encoding="utf-8").strip()


NATIVE_EXEC_PREFIX = _exec_prefix(NATIVE_EXECUTABLE)
NATIVE_EXEC_PREFIX_MSG = f"{NATIVE_EXEC_PREFIX} is the exec_prefix"


@pytest.fixture(autouse=True)
def projdir(tmp_path, monkeypatch):
    pwd = tmp_path / "projdir"
    pwd.mkdir()
    for fname in "tox.ini", "setup.py":
        shutil.copy(FIXTURES_DIR / fname, pwd)
    monkeypatch.chdir(pwd)
    return pwd


@pytest.fixture(params=('--print-deps-only', '--print-deps-to-file=-', '--print-deps-to=-'))
def print_deps_stdout_arg(request):
    """Argument for printing deps to stdout"""
    return request.param


@pytest.fixture(params=('--print-extras-to-file=-', '--print-extras-to=-'))
def print_extras_stdout_arg(request):
    """Argument for printing extras to stdout"""
    return request.param


@contextlib.contextmanager
def modify_config(tox_ini_path):
    """Context manager that allows modifying the given Tox config file

    A statement like::

        with prepare_config(projdir) as config:

    will make `config` a ConfigParser instance that is saved at the end
    of the `with` block.
    """
    config = configparser.ConfigParser()
    config.read(tox_ini_path)
    yield config
    with open(tox_ini_path, 'w') as tox_ini_file:
        config.write(tox_ini_file)


def tox(*args, quiet=True, **kwargs):
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("stderr", subprocess.PIPE)
    kwargs.setdefault("check", True)
    q = ("-q",) if quiet else ()
    try:
        cp = subprocess.run((sys.executable, "-m", "tox") + q + args, **kwargs)
    except subprocess.CalledProcessError as e:
        print(e.stdout, file=sys.stdout)
        print(e.stderr, file=sys.stderr)
        raise
    print(cp.stdout, file=sys.stdout)
    print(cp.stderr, file=sys.stderr)
    return cp


TOX_VERSION = ver(tox("--version").stdout.split(" ")[0])


@functools.lru_cache(maxsize=8)
def is_available(python):
    try:
        subprocess.run((python, "--version"))
    except FileNotFoundError:
        return False
    return True


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
def test_print_deps(toxenv, print_deps_stdout_arg):
    result = tox("-e", toxenv, print_deps_stdout_arg)
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


@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38", "py39"])
def test_print_deps_with_tox_minversion(projdir, toxenv, print_deps_stdout_arg):
    with modify_config(projdir / 'tox.ini') as config:
        config["tox"]["minversion"] = "3.13"
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = textwrap.dedent(
        f"""
        tox >= 3.13
        six
        py
        ___________________________________ summary ____________________________________
          {toxenv}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


@pytest.mark.xfail(TOX_VERSION < ver("3.22"), reason="No support in old tox")
@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38", "py39"])
def test_print_deps_with_tox_requires(projdir, toxenv, print_deps_stdout_arg):
    with modify_config(projdir / 'tox.ini') as config:
        config["tox"]["requires"] = "\n    setuptools > 30\n    pluggy"
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = textwrap.dedent(
        f"""
        setuptools > 30
        pluggy
        six
        py
        ___________________________________ summary ____________________________________
          {toxenv}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


@pytest.mark.xfail(TOX_VERSION < ver("3.22"), reason="No support in old tox")
@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38", "py39"])
def test_print_deps_with_tox_minversion_and_requires(projdir, toxenv, print_deps_stdout_arg):
    with modify_config(projdir / 'tox.ini') as config:
        config["tox"]["minversion"] = "3.13"
        config["tox"]["requires"] = "\n    setuptools > 30\n    pluggy"
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = textwrap.dedent(
        f"""
        tox >= 3.13
        setuptools > 30
        pluggy
        six
        py
        ___________________________________ summary ____________________________________
          {toxenv}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38", "py39"])
def test_print_extras(toxenv, print_extras_stdout_arg):
    result = tox("-e", toxenv, print_extras_stdout_arg)
    expected = textwrap.dedent(
        f"""
        dev
        full
        ___________________________________ summary ____________________________________
          {toxenv}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38", "py39"])
def test_print_deps_only_deprecated(toxenv):
    result = tox(
        "-e", toxenv, '--print-deps-only',
        env={**os.environ, 'PYTHONWARNINGS': 'always'},
    )
    waring_text = (
        "DeprecationWarning: --print-deps-only is deprecated; "
        + "use `--print-deps-to -`"
    )
    assert waring_text in result.stderr


def test_allenvs_print_deps(print_deps_stdout_arg):
    result = tox(print_deps_stdout_arg)
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


def test_allenvs_print_extras(print_extras_stdout_arg):
    result = tox(print_extras_stdout_arg)
    expected = textwrap.dedent(
        """
        dev
        full
        dev
        full
        dev
        full
        dev
        full
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
    result = tox("-e", toxenv, "--print-deps-to", str(depspath))
    assert depspath.read_text().splitlines() == ["six", "py"]
    expected = textwrap.dedent(
        f"""
        ___________________________________ summary ____________________________________
          {toxenv}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


@pytest.mark.parametrize("toxenv", ["py36", "py37", "py38", "py39"])
def test_print_extras_to_file(toxenv, tmp_path):
    extraspath = tmp_path / "extras"
    result = tox("-e", toxenv, "--print-extras-to", str(extraspath))
    assert extraspath.read_text().splitlines() == ["dev", "full"]
    expected = textwrap.dedent(
        f"""
        ___________________________________ summary ____________________________________
          {toxenv}: commands succeeded
          congratulations :)
        """
    ).lstrip()
    assert result.stdout == expected


@pytest.mark.parametrize('option', ('--print-deps-to', '--print-deps-to-file'))
def test_allenvs_print_deps_to_file(tmp_path, option):
    depspath = tmp_path / "deps"
    result = tox(option, str(depspath))
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


@pytest.mark.parametrize('option', ('--print-extras-to', '--print-extras-to-file'))
def test_allenvs_print_extras_to_file(tmp_path, option):
    extraspath = tmp_path / "extras"
    result = tox(option, str(extraspath))
    assert extraspath.read_text().splitlines() == ["dev", "full"] * 4
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
    result = tox("--print-deps-to", str(depspath))
    lines = depspath.read_text().splitlines()
    assert "nada" not in lines
    assert "six" in lines
    assert "py" in lines


def test_allenvs_print_extras_to_existing_file(tmp_path):
    extraspath = tmp_path / "extras"
    extraspath.write_text("nada")
    result = tox("--print-extras-to", str(extraspath))
    lines = extraspath.read_text().splitlines()
    assert "nada" not in lines
    assert "dev" in lines
    assert "full" in lines


@pytest.mark.parametrize("deps_stdout", [True, False])
@pytest.mark.parametrize("extras_stdout", [True, False])
def test_allenvs_print_deps_to_file_print_extras_to_other_file(tmp_path, deps_stdout, extras_stdout):
    if deps_stdout and extras_stdout:
        pytest.xfail("Unsupported combination of parameters")

    depspath = "-" if deps_stdout else tmp_path / "deps"
    extraspath = "-" if extras_stdout else tmp_path / "extras"
    result = tox("--print-deps-to", str(depspath),
                 "--print-extras-to", str(extraspath))
    if deps_stdout:
        depslines = result.stdout.splitlines()
        extraslines = extraspath.read_text().splitlines()
    elif extras_stdout:
        depslines = depspath.read_text().splitlines()
        extraslines = result.stdout.splitlines()
    else:
        extraslines = extraspath.read_text().splitlines()
        depslines = depspath.read_text().splitlines()

    assert "six" in depslines
    assert "py" in depslines
    assert "full" in extraslines
    assert "dev" in extraslines

    assert "six" not in extraslines
    assert "py" not in extraslines
    assert "full" not in depslines
    assert "dev" not in depslines


def test_print_deps_extras_to_same_file_is_not_possible(tmp_path):
    depsextraspath = tmp_path / "depsextras"
    result = tox(
        "-e",
        NATIVE_TOXENV,
        "--print-deps-to", str(depsextraspath),
        "--print-extras-to", str(depsextraspath),
        check=False,
    )
    assert result.returncode > 0
    assert "cannot be identical" in result.stderr


def test_print_deps_extras_to_stdout_is_not_possible(
        tmp_path,
        print_deps_stdout_arg,
        print_extras_stdout_arg,):
    result = tox(
        "-e",
        NATIVE_TOXENV,
        print_deps_stdout_arg,
        print_extras_stdout_arg,
        check=False,
    )
    assert result.returncode > 0
    assert "cannot be identical" in result.stderr


def test_print_deps_only_print_deps_to_file_are_mutually_exclusive():
    result = tox(
        "-e",
        NATIVE_TOXENV,
        "--print-deps-only",
        "--print-deps-to",
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


def test_regular_after_first_print_deps_is_supported(print_deps_stdout_arg):
    result = tox("-e", NATIVE_TOXENV, print_deps_stdout_arg)
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


def test_current_after_print_deps(print_deps_stdout_arg):
    # this is quite fast, so we can do it several times
    for _ in range(3):
        result = tox("-e", NATIVE_TOXENV, print_deps_stdout_arg)
        assert "bin/python" not in result.stdout
        assert "six" in result.stdout
        result = tox("-re", NATIVE_TOXENV, "--current-env")
        assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG


def test_current_after_print_extras(print_extras_stdout_arg):
    # this is quite fast, so we can do it several times
    for _ in range(3):
        result = tox("-e", NATIVE_TOXENV, print_extras_stdout_arg)
        assert "bin/python" not in result.stdout
        assert "full" in result.stdout
        result = tox("-re", NATIVE_TOXENV, "--current-env")
        assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG


def test_regular_recreate_after_print_deps(print_deps_stdout_arg):
    result = tox("-e", NATIVE_TOXENV, print_deps_stdout_arg)
    assert "bin/python" not in result.stdout
    assert "six" in result.stdout

    result = tox("-re", NATIVE_TOXENV)
    assert result.stdout.splitlines()[0] != NATIVE_EXEC_PREFIX_MSG
    sitelib = DOT_TOX / f"{NATIVE_TOXENV}/lib/python3.{NATIVE_TOXENV[-1]}/site-packages"
    assert sitelib.is_dir()
    assert len(list(sitelib.glob("test-*.dist-info"))) == 1

    result = tox("-e", NATIVE_TOXENV, print_deps_stdout_arg)
    assert "bin/python" not in result.stdout
    assert "six" in result.stdout


def test_print_deps_without_python_command(tmp_path, print_deps_stdout_arg):
    bin = tmp_path / "bin"
    bin.mkdir()
    tox_link = bin / "tox"
    tox_path = shutil.which("tox")
    tox_link.symlink_to(tox_path)
    env = {**os.environ, "PATH": str(bin)}

    result = tox("-e", NATIVE_TOXENV, print_deps_stdout_arg, env=env)
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


@pytest.mark.parametrize("flag", [None, "--print-deps-to=-", "--current-env"])
def test_noquiet_installed_packages(flag):
    flags = (flag,) if flag else ()
    result = tox("-e", NATIVE_TOXENV, *flags, quiet=False, check=False)
    assert f"\n{NATIVE_TOXENV} installed: " in result.stdout
    for line in result.stdout.splitlines():
        if line.startswith(f"{NATIVE_TOXENV} installed: "):
            packages = line.rpartition(" installed: ")[-1].split(",")
            break

    # default tox produces output sorted by package names
    assert packages == sorted(
        packages, key=lambda p: p.partition("==")[0].partition(" @ ")[0].lower()
    )

    # without a flag, the output must match tox defaults
    if not flag:
        assert len(packages) == 3
        assert packages[0].startswith("py==")
        assert packages[1].startswith("six==")
        assert packages[2].startswith(("test==", "test @ "))  # old and new pip

    # with our flags, uses the absolutely current environment by default, hence has tox
    else:
        assert len([p for p in packages if p.startswith("tox==")]) == 1
        assert all(re.match(r"\S+==\S+", p) for p in packages)


@pytest.mark.parametrize("flag", ["--print-deps-to=-", "--print-extras-to=-", "--current-env"])
@pytest.mark.parametrize("usedevelop", [True, False])
def test_self_is_not_installed(projdir, flag, usedevelop):
    with modify_config(projdir / 'tox.ini') as config:
        config['testenv']['usedevelop'] = str(usedevelop)
    result = tox("-e", NATIVE_TOXENV, flag, quiet=False)
    assert 'test==0.0.0' not in result.stdout
    assert 'test @ file://' not in result.stdout


@pytest.mark.parametrize("usedevelop", [True, False])
def test_self_is_installed_with_regular_tox(projdir, usedevelop):
    with modify_config(projdir / 'tox.ini') as config:
        config['testenv']['usedevelop'] = str(usedevelop)
    result = tox("-e", NATIVE_TOXENV, quiet=False)
    assert ('test==0.0.0' in result.stdout or
            'test @ file://' in result.stdout)
