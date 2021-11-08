from tox import __version__ as TOX_VERSION

if TOX_VERSION[0] == "4":
    from tox_current_env.hooks4 import *
else:
    from tox_current_env.hooks3 import *
