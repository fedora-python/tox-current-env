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
    """Stores options in the config. Makes all commands external"""
    if config.option.print_deps_only:
        config.skipsdist = True
    elif config.option.current_env:
        config.option.recreate = True
        config.skipsdist = True
        for testenv in config.envconfigs:
            config.envconfigs[testenv].whitelist_externals = "*"

    return config


@tox.hookimpl
def tox_testenv_create(venv, action):
    """We don't create anything"""
    config = venv.envconfig.config
    if config.option.current_env or config.option.print_deps_only:
        # Make sure the `python` command on path is sys.executable.
        # (We might have e.g. /usr/bin/python3, not `python`.)
        # Remove the rest of the virtualenv.
        link = venv.envconfig.get_envpython()
        target = sys.executable
        shutil.rmtree(os.path.dirname(link), ignore_errors=True)
        os.makedirs(os.path.dirname(link))
        os.symlink(target, link)
        return True


@tox.hookimpl
def tox_testenv_install_deps(venv, action):
    """We don't install anything"""
    config = venv.envconfig.config
    if config.option.current_env or config.option.print_deps_only:
        return True


@tox.hookimpl
def tox_runtest(venv, redirect):
    if venv.envconfig.config.option.print_deps_only:
        for dependency in venv.get_resolved_dependencies():
            print(dependency)
        return True
