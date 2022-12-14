import os
import re
import shutil
import textwrap

import pytest

from utils import (
    DOT_TOX,
    NATIVE_EXEC_PREFIX_MSG,
    NATIVE_SITE_PACKAGES,
    NATIVE_TOXENV,
    TOX_VERSION,
    TOX_MIN_VERSION,
    envs_from_tox_ini,
    modify_config,
    needs_all_pythons,
    prep_tox_output,
    tox,
    tox_footer,
)


if TOX_VERSION.major != 4:
    pytest.skip("skipping tests for tox 4", allow_module_level=True)


def test_native_toxenv_current_env():
    result = tox("-e", NATIVE_TOXENV, "--current-env")
    assert result.stdout.splitlines()[0] == NATIVE_EXEC_PREFIX_MSG
    assert not (DOT_TOX / NATIVE_TOXENV / "lib").is_dir()


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_deps(toxenv, print_deps_stdout_arg):
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = textwrap.dedent(
        f"""
        tox>={TOX_MIN_VERSION}
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip()
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
    expected = textwrap.dedent(
        f"""
        tox>={TOX_MIN_VERSION}
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip()
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
    expected = textwrap.dedent(
        f"""
        setuptools>30
        pluggy
        tox>={TOX_MIN_VERSION}
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip()
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_deps_with_tox_minversion_and_requires(
    projdir, toxenv, print_deps_stdout_arg
):
    with modify_config(projdir / "tox.ini") as config:
        config["tox"]["minversion"] = "3.13"
        config["tox"]["requires"] = "\n    setuptools > 30\n    pluggy"
    result = tox("-e", toxenv, print_deps_stdout_arg)
    expected = textwrap.dedent(
        f"""
        setuptools>30
        pluggy
        tox>=3.13
        six
        py
        {tox_footer(toxenv)}
        """
    ).lstrip()
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_extras(toxenv, print_extras_stdout_arg):
    result = tox("-e", toxenv, print_extras_stdout_arg)
    expected = textwrap.dedent(
        f"""
        dev
        full
        {tox_footer(toxenv)}
        """
    ).lstrip()
    assert sorted(prep_tox_output(result.stdout).splitlines()) == sorted(
        expected.splitlines()
    )


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
@pytest.mark.parametrize("pre_post", ["pre", "post", "both"])
def test_print_extras_with_commands_pre_post(projdir, toxenv, pre_post, print_extras_stdout_arg):
    with modify_config(projdir / 'tox.ini') as config:
        if pre_post == "both":
            config["testenv"]["commands_pre"] = "echo unexpected"
            config["testenv"]["commands_post"] = "echo unexpected"
        else:
            config["testenv"][f"commands_{pre_post}"] = "echo unexpected"
    result = tox("-e", toxenv, print_extras_stdout_arg)
    expected = textwrap.dedent(
        f"""
        dev
        full
        {tox_footer(toxenv)}
        """
    ).lstrip()
    assert sorted(prep_tox_output(result.stdout).splitlines()) == sorted(
        expected.splitlines()
    )
    assert result.stderr == ""


def test_allenvs_print_deps(print_deps_stdout_arg):
    result = tox(print_deps_stdout_arg)
    expected = []
    for env in envs_from_tox_ini():
        expected.extend((f"tox>={TOX_MIN_VERSION}", "six", "py", f"{env}: OK"))
    expected.pop()  # The last "py310: OK" is not there
    expected.append(tox_footer(spaces=0))
    expected = ("\n".join(expected)).splitlines()
    assert sorted(prep_tox_output(result.stdout).splitlines()) == sorted(expected)


def test_allenvs_print_extras(print_extras_stdout_arg):
    result = tox(print_extras_stdout_arg)
    expected = []
    for env in envs_from_tox_ini():
        expected.extend(("dev", "full", f"{env}: OK"))
    expected.pop()  # The last "py310: OK" is not there
    expected.append(tox_footer(spaces=0))
    expected = ("\n".join(expected)).splitlines()
    assert sorted(prep_tox_output(result.stdout).splitlines()) == sorted(expected)


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_deps_to_file(toxenv, tmp_path):
    depspath = tmp_path / "deps"
    result = tox("-e", toxenv, "--print-deps-to", str(depspath))
    assert sorted(depspath.read_text().splitlines()) == sorted(
        [f"tox>={TOX_MIN_VERSION}", "six", "py"]
    )
    expected = tox_footer(toxenv, spaces=0) + "\n"
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("toxenv", envs_from_tox_ini())
def test_print_extras_to_file(toxenv, tmp_path):
    extraspath = tmp_path / "extras"
    result = tox("-e", toxenv, "--print-extras-to", str(extraspath))
    assert sorted(extraspath.read_text().splitlines()) == sorted(["dev", "full"])
    expected = tox_footer(toxenv, spaces=0) + "\n"
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("option", ("--print-deps-to", "--print-deps-to-file"))
def test_allenvs_print_deps_to_file(tmp_path, option):
    depspath = tmp_path / "deps"
    result = tox(option, str(depspath))
    assert sorted(depspath.read_text().splitlines()) == sorted(
        [f"tox>={TOX_MIN_VERSION}", "six", "py"] * len(envs_from_tox_ini())
    )
    expected = ""
    for env in envs_from_tox_ini()[:-1]:
        expected += f"{env}: OK\n"
    expected += tox_footer(spaces=0) + "\n"
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("option", ("--print-extras-to", "--print-extras-to-file"))
def test_allenvs_print_extras_to_file(tmp_path, option):
    extraspath = tmp_path / "extras"
    result = tox(option, str(extraspath))
    assert sorted(extraspath.read_text().splitlines()) == sorted(
        ["dev", "full"] * len(envs_from_tox_ini())
    )
    expected = ""
    for env in envs_from_tox_ini()[:-1]:
        expected += f"{env}: OK\n"
    expected += tox_footer(spaces=0) + "\n"
    assert prep_tox_output(result.stdout) == expected


def test_allenvs_print_deps_to_existing_file(tmp_path):
    depspath = tmp_path / "deps"
    depspath.write_text("nada")
    _ = tox("--print-deps-to", str(depspath))
    lines = depspath.read_text().splitlines()
    assert "nada" not in lines
    assert "six" in lines
    assert "py" in lines


def test_allenvs_print_extras_to_existing_file(tmp_path):
    extraspath = tmp_path / "extras"
    extraspath.write_text("nada")
    _ = tox("--print-extras-to", str(extraspath))
    lines = extraspath.read_text().splitlines()
    assert "nada" not in lines
    assert "dev" in lines
    assert "full" in lines


@pytest.mark.parametrize("deps_stdout", [True, False])
@pytest.mark.parametrize("extras_stdout", [True, False])
def test_allenvs_print_deps_to_file_print_extras_to_other_file(
    tmp_path, deps_stdout, extras_stdout
):
    if deps_stdout and extras_stdout:
        pytest.xfail("Unsupported combination of parameters")

    depspath = "-" if deps_stdout else tmp_path / "deps"
    extraspath = "-" if extras_stdout else tmp_path / "extras"
    result = tox("--print-deps-to", str(depspath), "--print-extras-to", str(extraspath))
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
        "--print-deps-to",
        str(depsextraspath),
        "--print-extras-to",
        str(depsextraspath),
        check=False,
    )
    assert result.returncode > 0
    assert "cannot be identical" in result.stderr


def test_print_deps_extras_to_stdout_is_not_possible(
    tmp_path,
    print_deps_stdout_arg,
    print_extras_stdout_arg,
):
    result = tox(
        "-e",
        NATIVE_TOXENV,
        print_deps_stdout_arg,
        print_extras_stdout_arg,
        check=False,
    )
    assert result.returncode > 0
    assert "cannot be identical" in result.stderr


@needs_all_pythons
def test_regular_run():
    result = tox()
    lines = result.stdout.splitlines()[:5]
    for line, env in zip(lines, envs_from_tox_ini()):
        assert f"/.tox/{env} is the exec_prefix" in line
    assert "congratulations" in result.stdout
    for env in envs_from_tox_ini():
        major, minor = re.match(r"py(\d)(\d+)", env).groups()
        for pkg in "py", "six", "test":
            sitelib = DOT_TOX / f"{env}/lib/python{major}.{minor}/site-packages"
            assert sitelib.is_dir()
            assert len(list(sitelib.glob(f"{pkg}-*.dist-info"))) == 1


def test_regular_run_native_toxenv():
    result = tox("-e", NATIVE_TOXENV)
    lines = sorted(result.stdout.splitlines()[:1])
    assert f"/.tox/{NATIVE_TOXENV} is the exec_prefix" in lines[0]
    assert "congratulations" in result.stdout
    for pkg in "py", "six", "test":
        sitelib = DOT_TOX / f"{NATIVE_TOXENV}/{NATIVE_SITE_PACKAGES}"
        assert sitelib.is_dir()
        assert len(list(sitelib.glob(f"{pkg}-*.dist-info"))) == 1


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
        tox>={TOX_MIN_VERSION}
        six
        py
        {tox_footer(NATIVE_TOXENV)}
        """
    ).lstrip()
    assert prep_tox_output(result.stdout) == expected


@pytest.mark.parametrize("flag", ["--print-deps-to=-", "--current-env"])
def test_recreate_environment(flag):
    flags = (flag,) if flag else ()
    _ = tox("-e", NATIVE_TOXENV, check=False)
    result = tox("-e", NATIVE_TOXENV, *flags, quiet=False, check=False)
    assert f"{NATIVE_TOXENV}: recreate env because env type changed" in prep_tox_output(
        result.stdout
    )


@pytest.mark.parametrize(
    "flag", ["--print-deps-to=-", "--print-extras-to=-", "--current-env"]
)
@pytest.mark.parametrize("usedevelop", [True, False])
def test_self_is_not_installed(projdir, flag, usedevelop):
    with modify_config(projdir / "tox.ini") as config:
        config["testenv"]["usedevelop"] = str(usedevelop)
    _ = tox("-e", NATIVE_TOXENV, flag, quiet=False)
    egg_link = DOT_TOX / f"{NATIVE_TOXENV}/{NATIVE_SITE_PACKAGES}" / "test.egg-link"
    dist_info = (
        DOT_TOX / f"{NATIVE_TOXENV}/{NATIVE_SITE_PACKAGES}" / "test-0.0.0.dist-info"
    )
    assert not egg_link.exists()
    assert not dist_info.exists()


@pytest.mark.parametrize("usedevelop", [True, False])
def test_self_is_installed_with_regular_tox(projdir, usedevelop):
    with modify_config(projdir / "tox.ini") as config:
        config["testenv"]["usedevelop"] = str(usedevelop)
    result = tox("-e", NATIVE_TOXENV, "-v", quiet=False)
    assert "test-0.0.0" in result.stdout
    if usedevelop:
        assert "test-0.0.0-0.editable" in result.stdout


@pytest.mark.parametrize("passenv", [None, "different list", "__var", "*"])
def test_passenv(projdir, passenv):
    with modify_config(projdir / "tox.ini") as config:
        config["testenv"]["commands"] = """python -c 'import os; print(os.getenv("__var"))'"""
        if passenv is not None:
            existing = config["testenv"].get("passenv", "") + " "
            config["testenv"]["passenv"] = existing + passenv
    env = {"__var": "assertme"}
    result = tox("-e", NATIVE_TOXENV, "--current-env", env=env, quiet=False)
    assert result.returncode == 0
    assert "\nassertme\n" in result.stdout
    assert "\nNone\n" not in result.stdout


@pytest.mark.parametrize("pass_env", [None, "different\nlist", "__var", "*"])
def test_pass_env(projdir, pass_env):
    with modify_config(projdir / "tox.ini") as config:
        config["testenv"]["commands"] = """python -c 'import os; print(os.getenv("__var"))'"""
        if pass_env is not None:
            config["testenv"]["pass_env"] = pass_env
    env = {"__var": "assertme"}
    result = tox("-e", NATIVE_TOXENV, "--current-env", env=env, quiet=False)
    assert result.returncode == 0
    assert "\nassertme\n" in result.stdout
    assert "\nNone\n" not in result.stdout
