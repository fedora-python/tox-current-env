import textwrap

import pytest

from utils import (
    DOT_TOX,
    NATIVE_EXEC_PREFIX_MSG,
    NATIVE_EXECUTABLE,
    NATIVE_SITE_PACKAGES,
    NATIVE_TOXENV,
    TOX_VERSION,
    TOX4,
    envs_from_tox_ini,
    modify_config,
    expand_tox,
    prep_tox_output,
    tox,
    tox_footer,
)


def test_native_toxenv_current_env():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG
    assert not (DOT_TOX / NATIVE_TOXENV / "lib").is_dir()


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_deps(toxenv, print_deps_stdout_arg):
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = expand_tox(textwrap.dedent(
        f"""
        [[TOX4:tox]]
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip())
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
@pytest.mark.parametrize("pre_post", ["pre", "post", "both"])
def test_print_deps_with_commands_pre_post(projdir, toxenv, pre_post, print_deps_stdout_arg):
    with modify_config(projdir / 'tox.ini') as config:
        if pre_post == "both":
            config["testenv"]["commands_pre"] = "echo unexpected"
            config["testenv"]["commands_post"] = "echo unexpected"
        else:
            config["testenv"][f"commands_{pre_post}"] = "echo unexpected"
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = expand_tox(textwrap.dedent(
        f"""
        [[TOX4:tox]]
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip())
    assert sorted(prep_tox_output(result.stdout).splitlines()) == sorted(
        expected.splitlines()
    )
    assert result.stderr == ""


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_deps_with_tox_minversion(projdir, toxenv, print_deps_stdout_arg):
    with modify_config(projdir / "tox.ini") as config:
        config["tox"]["minversion"] = "3.13"
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = textwrap.dedent(
        f"""
        tox>=3.13
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip()
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_deps_with_tox_requires(projdir, toxenv, print_deps_stdout_arg):
    with modify_config(projdir / "tox.ini") as config:
        config["tox"]["requires"] = "\n    setuptools > 30\n    pluggy"
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = expand_tox(textwrap.dedent(
        f"""
        setuptools>30
        pluggy
        [[TOX4:tox]]
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip())
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_deps_with_tox_minversion_and_requires(
    projdir, toxenv, print_deps_stdout_arg
):
    with modify_config(projdir / "tox.ini") as config:
        config["tox"]["minversion"] = "3.13"
        config["tox"]["requires"] = "\n    setuptools > 30\n    pluggy"
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = expand_tox(textwrap.dedent(
        f"""
        [[TOX3:tox>=3.13]]
        setuptools>30
        pluggy
        [[TOX4:tox>=3.13]]
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip())
    assert prep_tox_output(result.stdout) == expected
