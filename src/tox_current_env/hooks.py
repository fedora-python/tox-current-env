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
        help="Don't run tests, only print the dependencies to stdout",
    )
    parser.add_argument(
        "--print-deps-to-file",
        action="store",
        dest="print_deps_path",
        metavar="PATH",
        default=None,
        help="Like --print-deps-only, but to a file. Overwrites the file if it exists.",
    )


@tox.hookimpl
def tox_configure(config):
    """Stores options in the config. Makes all commands external and skips sdist"""
    if config.option.print_deps_only and config.option.print_deps_path:
        raise tox.exception.ConfigError(
            "--print-deps-only cannot be used together with --print-deps-to-file"
        )
    if config.option.print_deps_path is not None:
        config.option.print_deps_only = True
        with open(config.option.print_deps_path, "w", encoding="utf-8") as f:
            f.write("")
    if config.option.current_env or config.option.print_deps_only:
        config.skipsdist = True
        for testenv in config.envconfigs:
            config.envconfigs[testenv].whitelist_externals = "*"

    return config


class InterpreterMismatch(tox.exception.InterpreterNotFound):
    """Interpreter version in current env does not match requested version"""


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


def is_any_env(venv):
    python, activate = _python_activate_exists(venv)
    return python


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
def tox_testenv_create(venv, action):
    """We create a fake virtualenv with just the symbolic link"""
    config = venv.envconfig.config
    create_fake_env = check_version = config.option.current_env
    if config.option.print_deps_only:
        if is_any_env(venv):
            # We don't need anything
            return True
        else:
            # We need at least some kind of environment,
            # or tox fails without a python command
            # We fallback to --current-env behavior,
            # because it's cheaper, faster and won't install stuff
            create_fake_env = True
    if check_version:
        # With real --current-env, we check this, but not with --print-deps-only only
        version_info = venv.envconfig.python_info.version_info
        if version_info is None:
            raise tox.exception.InterpreterNotFound(venv.envconfig.basepython)
        if version_info[:2] != sys.version_info[:2]:
            raise InterpreterMismatch(
                f"tox_current_env: interpreter versions do not match:\n"
                + f"    in current env: {tuple(sys.version_info)}\n"
                + f"    requested: {version_info}"
            )
    if create_fake_env:
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


@tox.hookimpl
def tox_package(session, venv):
    """Fail early when unsupported"""
    config = venv.envconfig.config
    unsupported_raise(config, venv)


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
    if config.option.print_deps_path is not None:
        with open(config.option.print_deps_path, "a", encoding="utf-8") as f:
            print(*venv.get_resolved_dependencies(), sep="\n", file=f)
        return True
    if config.option.print_deps_only:
        print(*venv.get_resolved_dependencies(), sep="\n")
        return True
