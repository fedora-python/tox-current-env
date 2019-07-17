import tox


@tox.hookimpl
def tox_testenv_create(venv, action):
    ...
