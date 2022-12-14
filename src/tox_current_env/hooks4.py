import argparse
import os
import platform
import sys
import sysconfig
from pathlib import Path
from typing import Set

from tox.config.loader.memory import MemoryLoader
from tox.execute.local_sub_process import (
    Execute,
    LocalSubProcessExecuteInstance,
)
from tox.plugin import impl
from tox.tox_env.python.api import PythonInfo
from tox.tox_env.python.runner import PythonRun


@impl
def tox_register_tox_env(register):
    register.add_run_env(CurrentEnv)
    register.add_run_env(PrintEnv)


@impl
def tox_add_option(parser):
    parser.add_argument(
        "--current-env",
        action="store_true",
        dest="current_env",
        default=False,
        help="Run tests in current environment, not creating any virtual environment",
    )
    parser.add_argument(
        "--print-deps-to",
        "--print-deps-to-file",
        action="store",
        type=argparse.FileType("w"),
        metavar="FILE",
        default=False,
        help="Don't run tests, only print the dependencies to the given file "
        + "(use `-` for stdout)",
    )
    parser.add_argument(
        "--print-extras-to",
        "--print-extras-to-file",
        action="store",
        type=argparse.FileType("w"),
        metavar="FILE",
        default=False,
        help="Don't run tests, only print the  names of the required extras to the given file "
        + "(use `-` for stdout)",
    )


@impl
def tox_add_core_config(core_conf, state):
    opt = state.conf.options

    if opt.current_env or opt.print_deps_to or opt.print_extras_to:
        # We do not want to install the main package.
        # no_package is the same as skipsdist.
        loader = MemoryLoader(no_package=True)
        core_conf.loaders.insert(0, loader)

    if opt.current_env:
        opt.default_runner = "current-env"
        return

    if getattr(opt.print_deps_to, "name", object()) == getattr(
        opt.print_extras_to, "name", object()
    ):
        raise RuntimeError(
            "The paths given to --print-deps-to and --print-extras-to cannot be identical."
        )

    if opt.print_deps_to or opt.print_extras_to:
        opt.default_runner = "print-env"
        return

    # No options used - switch back to the standard runner
    # Workaround for: https://github.com/tox-dev/tox/issues/2264
    opt.default_runner = "virtualenv"


@impl
def tox_add_env_config(env_conf, state):
    opt = state.conf.options
    # This allows all external commands.
    # All of them are external for us.
    # Because tox 4 no longer reads $TOX_TESTENV_PASSENV,
    # this plugin always passes all environment variables by default.
    if opt.current_env:
        allow_external_cmds = MemoryLoader(allowlist_externals=["*"], pass_env=["*"])
        env_conf.loaders.insert(0, allow_external_cmds)
    # For print-deps-to and print-extras-to, use empty
    # list of commands so the tox does nothing.
    if opt.print_deps_to or opt.print_extras_to:
        empty_commands = MemoryLoader(commands=[], commands_pre=[], commands_post=[])
        env_conf.loaders.insert(0, empty_commands)


class Installer:
    """Noop installer"""

    def install(self, *args, **kwargs):
        return None


class CurrentEnvLocalSubProcessExecutor(Execute):
    def build_instance(
        self,
        request,
        options,
        out,
        err,
    ):
        request.env["PATH"] = ":".join(
            (str(options._env.env_dir / "bin"), request.env.get("PATH", ""))
        )
        return LocalSubProcessExecuteInstance(request, options, out, err)


class CurrentEnv(PythonRun):
    def __init__(self, create_args):
        self._executor = None
        self._installer = None
        self._path = []
        super().__init__(create_args)

    @staticmethod
    def id():
        return "current-env"

    @property
    def _default_package_tox_env_type(self):
        return None

    @property
    def _external_pkg_tox_env_type(self):
        return None

    @property
    def _package_tox_env_type(self):
        return None

    @property
    def executor(self):
        if self._executor is None:
            self._executor = CurrentEnvLocalSubProcessExecutor(self.options.is_colored)
        return self._executor

    def _get_python(self, base_python):
        return PythonInfo(
            implementation=sys.implementation,
            version_info=sys.version_info,
            version=sys.version,
            is_64=(platform.architecture()[0] == "64bit"),
            platform=platform.platform(),
            extra={"executable": Path(sys.executable)},
        )

    def create_python_env(self):
        """Fake Python environment just to make sure all possible
        commands like python or python3 works."""
        bindir = self.env_dir / "bin"
        if not bindir.exists():
            os.mkdir(bindir)
        for suffix in (
            "",
            f"{sys.version_info.major}",
            f"{sys.version_info.major}.{sys.version_info.minor}",
        ):
            symlink = bindir / f"python{suffix}"
            if not symlink.exists():
                os.symlink(sys.executable, symlink)

    def env_bin_dir(self):
        return Path(sysconfig.get_path("scripts"))

    def env_python(self):
        return sys.executable

    def env_site_package_dir(self):
        return Path(sysconfig.get_path("purelib"))

    @property
    def installer(self):
        return Installer()

    def prepend_env_var_path(self):
        return [self.env_bin_dir()]

    @property
    def runs_on_platform(self):
        return sys.platform


class PrintEnv(CurrentEnv):
    def __init__(self, create_args):
        super().__init__(create_args)

        if self.options.print_extras_to:
            if "extras" not in self.conf:
                # Unfortunately, if there is skipsdist/no_package or skip_install
                # in the config, this section is not parsed at all so we have to
                # do it here manually to be able to read its content.
                self.conf.add_config(
                    keys=["extras"],
                    of_type=Set[str],
                    default=set(),
                    desc="extras to install of the target package",
                )

    def create_python_env(self):
        """We don't need any environment for this plugin"""
        return None

    def prepend_env_var_path(self):
        """Usage of this method for the core of this plugin is far from perfect
        but this method is called every time even without recreated environment"""
        if self.options.print_deps_to:
            print(
                *self.core["requires"],
                *self.conf["deps"].lines(),
                sep="\n",
                file=self.options.print_deps_to,
            )
            self.options.print_deps_to.flush()

        if self.options.print_extras_to:
            print(
                *self.conf["extras"],
                sep="\n",
                file=self.options.print_extras_to,
            )
            self.options.print_extras_to.flush()

    @staticmethod
    def id():
        return "print-env"
