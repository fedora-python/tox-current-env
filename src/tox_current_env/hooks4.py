import argparse
import platform
import sys
import sysconfig
import warnings
from pathlib import Path
from typing import Set

from tox.execute.api import Execute
from tox.execute.local_sub_process import LocalSubProcessExecuteInstance
from tox.plugin import impl
from tox.report import HandledError
from tox.tox_env.python.api import PythonInfo
from tox.tox_env.python.pip.pip_install import Pip
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
def tox_add_core_config(core_conf, config):
    if config.options.current_env:
        config.options.default_runner = "current-env"
        return

    if getattr(config.options.print_deps_to, "name", object()) == getattr(
        config.options.print_extras_to, "name", object()
    ):
        raise RuntimeError(
            "The paths given to --print-deps-to and --print-extras-to cannot be identical."
        )

    if config.options.print_deps_to or config.options.print_extras_to:
        config.options.default_runner = "print-env"
        return

    # No options used - switch back to the standard runner
    # Workaround for: https://github.com/tox-dev/tox/issues/2264
    config.options.default_runner = "virtualenv"


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
            self._executor = CurrentEnvRunExecutor(self.options.is_colored)
        return self._executor

    def _get_python(self, base_python):
        # TODO: Improve version check and error message
        version_nodot = "".join(str(p) for p in sys.version_info[:2])
        base_python = base_python[0]
        if not base_python.endswith(version_nodot):
            raise HandledError(
                "Python version mismatch. "
                f"Current version: {sys.version_info[:2]}, "
                f"Requested environment: {base_python}"
            )

        return PythonInfo(
            implementation=sys.implementation,
            version_info=sys.version_info,
            version=sys.version,
            is_64=(platform.architecture()[0] == "64bit"),
            platform=platform.platform(),
            extra={"executable": Path(sys.executable)},
        )

    def create_python_env(self):
        return None

    def env_bin_dir(self):
        return Path(sysconfig.get_path("scripts"))

    def env_python(self):
        return sys.executable

    def env_site_package_dir(self):
        return Path(sysconfig.get_path("purelib"))

    @property
    def installer(self):
        if self._installer is None:
            self._installer = Pip(self)
        return self._installer

    def prepend_env_var_path(self):
        return [self.env_bin_dir()]

    @property
    def runs_on_platform(self):
        return sys.platform


class CurrentEnvRunExecutor(Execute):
    def build_instance(
        self,
        request,
        options,
        out,
        err,
    ):
        # Disable check for the external commands,
        # all of them are external for us.
        request.allow = None
        return LocalSubProcessExecuteInstance(request, options, out, err)


class PrintEnv(CurrentEnv):
    def __init__(self, create_args):
        super().__init__(create_args)

        # As soon as this environment has enough info to do its job,
        # do it and nothing more.

        if self.options.print_deps_to:
            print(
                *self.core["requires"],
                *self.conf["deps"].lines(),
                sep="\n",
                file=self.options.print_deps_to,
            )
            self.options.print_deps_to.flush()

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
            print(
                *self.conf["extras"],
                sep="\n",
                file=self.options.print_extras_to,
            )
            self.options.print_extras_to.flush()

        # We are done
        sys.exit(0)

    @staticmethod
    def id():
        return "print-env"