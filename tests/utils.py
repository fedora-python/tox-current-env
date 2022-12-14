import configparser
import contextlib
import functools
import os
import pathlib
import re
import subprocess
import sys
from configparser import ConfigParser

import pytest
from packaging.version import parse as ver

PYTHON_VERSION_DOT = f"{sys.version_info[0]}.{sys.version_info[1]}"
PYTHON_VERSION_NODOT = f"{sys.version_info[0]}{sys.version_info[1]}"
NATIVE_TOXENV = f"py{PYTHON_VERSION_NODOT}"
NATIVE_SITE_PACKAGES = f"lib/python{PYTHON_VERSION_DOT}/site-packages"
NATIVE_EXECUTABLE = str(pathlib.Path(sys.executable).resolve())
FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
DOT_TOX = pathlib.Path("./.tox")


def _exec_prefix(executable):
    """Returns sys.exec_prefix for the given executable"""
    cmd = (executable, "-c", "import sys; print(sys.exec_prefix)")
    return subprocess.check_output(cmd, encoding="utf-8").strip()


NATIVE_EXEC_PREFIX = _exec_prefix(NATIVE_EXECUTABLE)
NATIVE_EXEC_PREFIX_MSG = f"{NATIVE_EXEC_PREFIX} is the exec_prefix"


def tox(*args, quiet=True, **kwargs):
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("stderr", subprocess.PIPE)
    kwargs.setdefault("check", True)
    kwargs.setdefault("cwd", os.getcwd())
    q = ("-q",) if quiet else ()
    env = dict(os.environ)
    env.pop("TOX_WORK_DIR", None)
    kwargs["env"] = {**env, **kwargs.get("env", {})}
    try:
        print("current", os.getcwd(), "running in", kwargs["cwd"])
        cp = subprocess.run((sys.executable, "-m", "tox") + q + args, **kwargs)
    except subprocess.CalledProcessError as e:
        print(e.stdout, file=sys.stdout)
        print(e.stderr, file=sys.stderr)
        raise
    print(cp.stdout, file=sys.stdout)
    print(cp.stderr, file=sys.stderr)
    return cp


TOX_VERSION = ver(tox("--version").stdout.split(" ")[0].split("+")[0])
TOX_MIN_VERSION = ver(f"{TOX_VERSION.major}.{TOX_VERSION.minor}")
TOX4 = TOX_VERSION.major == 4


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
    with open(tox_ini_path, "w") as tox_ini_file:
        config.write(tox_ini_file)


@functools.lru_cache(maxsize=8)
def is_available(python):
    try:
        subprocess.run((python, "--version"))
    except FileNotFoundError:
        return False
    return True


@functools.lru_cache()
def envs_from_tox_ini():
    cp = ConfigParser()
    cp.read(FIXTURES_DIR / "tox.ini")
    return cp["tox"]["envlist"].split(",")


def tox_footer(envs=None, spaces=8):
    if envs is None:
        envs = envs_from_tox_ini()
    elif isinstance(envs, str):
        envs = [envs]

    default_indent = " " * spaces

    if TOX4:
        result = ""
    else:
        result = "___________________________________ summary ____________________________________\n"

    for i, env in enumerate(envs):
        if TOX4:
            # Skip indentation for the first line
            indent = default_indent if i > 0 else ""
            result += f"{indent}  {env}: OK\n"
        else:
            result += f"{default_indent}  {env}: commands succeeded\n"

    result += f"{default_indent}  congratulations :)"

    return result


def prep_tox_output(output):
    """Remove time info from tox output"""
    result = re.sub(r" \((\d+\.\d+|\d+) seconds\)", "", output)
    result = re.sub(r" ✔ in (\d+\.\d+|\d+) seconds", "", result)
    return result


needs_all_pythons = pytest.mark.skipif(
    not all((is_available(f"python3.{x}") for x in range(6, 12))),
    reason="This test needs all pythons from 3.6 to 3.11 available in $PATH",
)
