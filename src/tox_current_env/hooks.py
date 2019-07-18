import os
import shutil
import sys
import tox


@tox.hookimpl
def tox_addoption(parser):
    parser.add_argument(
        "--current-env",
        action="store_true",
        dest="current_env",
        default=False,
        help="Run tests in current environment, not creating any virtual environment",
    )
    parser.add_argument(
        "--print-deps-only",
        action="store_true",
        dest="print_deps_only",
        default=False,
        help="Don't run tests, only print the dependencies",
    )


@tox.hookimpl
def tox_configure(config):
    """Stores options in the config. Makes all commands external and skips sdist"""
    if config.option.current_env or config.option.print_deps_only:
        config.skipsdist = True
        for testenv in config.envconfigs:
            config.envconfigs[testenv].whitelist_externals = "*"

    return config


class InterpreterMismatch(tox.exception.InterpreterNotFound):
    """Interpreter version in current env does not match requested version"""


@tox.hookimpl
def tox_testenv_create(venv, action):
    """We create a fake virtualenv with just the symbolic link"""
    config = venv.envconfig.config
    if config.option.print_deps_only:
        # We don't need anything
        return True
    if config.option.current_env:
        version_info = venv.envconfig.python_info.version_info
        if version_info[:2] != sys.version_info[:2]:
            raise InterpreterMismatch(
                f"tox_current_env: interpreter versions do not match:\n"
                + f"    in current env: {tuple(sys.version_info)}\n"
                + f"    requested: {version_info}"
            )

        # Make sure the `python` command on path is sys.executable.
        # (We might have e.g. /usr/bin/python3, not `python`.)
        # Remove the rest of the virtualenv.
        link = venv.envconfig.get_envpython()
        target = sys.executable
        shutil.rmtree(os.path.dirname(os.path.dirname(link)), ignore_errors=True)
        os.makedirs(os.path.dirname(link))
        os.symlink(target, link)
        return True
    else:
        link = venv.envconfig.get_envpython()
        shutil.rmtree(os.path.dirname(os.path.dirname(link)), ignore_errors=True)
        return None  # let tox handle the rest


def _python_activate_exists(venv):
    python = venv.envconfig.get_envpython()
    bindir = os.path.dirname(python)
    activate = os.path.join(bindir, "activate")
    return os.path.exists(python), os.path.exists(activate)


def is_current_env_link(venv):
    python, activate = _python_activate_exists(venv)
    return python and not activate


def is_proper_venv(venv):
    python, activate = _python_activate_exists(venv)
    return python and activate


def unsupported_raise(config, venv):
    if config.option.recreate:
        return
    regular = not (config.option.current_env or config.option.print_deps_only)
    if regular and is_current_env_link(venv):
        raise tox.exception.ConfigError(
            "Regular tox run after --current-env or --print-deps-only tox run is not supported without --recreate (-r)."
        )
    elif config.option.current_env and is_proper_venv(venv):
        raise tox.exception.ConfigError(
            "--current-env after regular tox run is not supported without --recreate (-r)."
        )


@tox.hookimpl
def tox_testenv_install_deps(venv, action):
    """We don't install anything"""
    config = venv.envconfig.config
    unsupported_raise(config, venv)
    if config.option.current_env or config.option.print_deps_only:
        return True


@tox.hookimpl
def tox_runtest(venv, redirect):
    """If --print-deps-only, prints deps instead of running tests"""
    config = venv.envconfig.config
    unsupported_raise(config, venv)
    if config.option.print_deps_only:
        for dependency in venv.get_resolved_dependencies():
            print(dependency)
        return True
