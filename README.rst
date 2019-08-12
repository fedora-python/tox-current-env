===============
tox-current-env
===============
---------------------------------------------------------------------------------------
`tox <https://tox.readthedocs.io/>`_  plugin to run tests in current Python environment
---------------------------------------------------------------------------------------

The ``tox-current-env`` plugin adds two options:

``tox --current-env``
   Runs the tox testenv's ``commands`` in the current Python environment
   (that is, the environment where ``tox`` is invoked from and installed in).
   Unlike regular ``tox`` invocation, this installs no dependencies declared in ``deps``.
   An attempt to run this with a Python version that doesn't match will fail
   (if ``tox`` is invoked from an Python 3.7 environment, any non 3.7 testenv will fail).

``tox --print-deps-only`` / ``--print-deps-to-file``
    Instead of running any ``commands``,
    simply prints the declared dependencies in ``deps`` to the standard output or specified file.
    This is useful for preparing the current environment for the above.
    ``--print-deps-to-file`` will overwrite the file if it already exists.

Invoking ``tox`` without any of the above options should behave as regular ``tox`` invocation without this plugin.
Any deviation from this behavior is considered a bug.

The plugin disables *tox's way* of providing a testing environment,
but assumes that you supply one in *some other way*.
Always run ``tox`` with this plugin in a fresh isolated environment,
such as Python virtualenv, Linux container or chroot.
\
See other caveats below.


Motivation
----------

Obviously, ``tox`` was created to run tests in isolated Python virtual environments.
The ``--current-env`` flag totally defeats the purpose of ``tox``.
Why would anybody do that, you might ask?

Well, it turns out that ``tox`` became too popular and gained another purpose.

The Python ecosystem now has formal `specifications <https://packaging.python.org/specifications/>`_ for many pieces of package metadata like versions or dependencies.
However, there is no standardization yet for declaring *test dependencies* or *running tests*.
The most popular de-facto standard for that today is ``tox``,
and we expect a future standard to evolve from ``tox.ini``.
This plugin lets us use ``tox``'s dependency lists and testing commands for environments other than Python venvs.

We hope this plugin will enable community best practices around ``tox`` configuration
to grow to better accomodate non-virtualenv environments in general – for example,
Linux distros, Conda, or containers.

Specifically, this plugin was created for `Fedora <https://fedoralovespython.org/>`_'s needs.
When we package Python software as RPM packages, we try to run the project's test suite during package build.
However, we need to test if the software works integrated into Fedora,
not with packages downloaded from PyPI into a fresh environment.
By running the tests in *current environment*, we can achieve that.

If you are interested in the RPM packaging part of this,
see Fedora's `%pyproject RPM macros <https://src.fedoraproject.org/rpms/pyproject-rpm-macros>`_.


Installation
------------

Install this via ``pip``:

.. code-block:: console

   $ python -m pip install tox-current-env

Or install the development version by cloning `the git repository <https://github.com/fedora-python/tox-current-env>`_
and ``pip``-installing locally:

.. code-block:: console

   $ git clone https://github.com/fedora-python/tox-current-env
   $ cd tox-current-env
   $ python -m pip install -e .


Usage
-----

When the plugin is installed, use ``tox`` with ``--current-env`` or ``--print-deps-only`` and all the other options as usual. Assuming your ``tox`` is installed on Python 3.7:

.. code-block:: console

   $ tox -e py37 --current-env
   py37 create: /home/pythonista/projects/holy-grail/tests/.tox/py37
   py37 installed: ...list of packages from the current environment...
   py37 run-test-pre: PYTHONHASHSEED='3333333333'
   py37 run-test: commands...
   ...runs tests in current environment's Python...
   ___________________________________ summary ____________________________________
     py37: commands succeeded
     congratulations :)

Attempting to run the ``py36`` environment's test will fail:

.. code-block:: console

   $ tox -e py36 --current-env
   py36 create: /home/pythonista/projects/holy-grail/tests/.tox/py36
   ERROR: InterpreterMismatch: tox_current_env: interpreter versions do not match:
       in current env: (3, 7, 4, 'final', 0)
       requested: (3, 6, 9, 'final', 0)
   ___________________________________ summary ____________________________________
   ERROR:  py36: InterpreterMismatch: tox_current_env: interpreter versions do not match:
       in current env: (3, 7, 4, 'final', 0)
       requested: (3, 6, 9, 'final', 0)

To get list of test dependencies, run:

.. code-block:: console

   $ tox -e py37 --print-deps-only
   py37 create: /home/pythonista/projects/holy-grail/tests/.tox/py37
   py37 installed: ...you can see almost anything here...
   py37 run-test-pre: PYTHONHASHSEED='3333333333'
   dep1
   dep2
   ...
   ___________________________________ summary ____________________________________
     py37: commands succeeded
     congratulations :)


Caveats, warnings and limitations
---------------------------------

Use an isolated environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Running (especially third party software's) tests in your system Python environment is dangerous.
Always use this plugin in an isolated environment,
such as Python virtualenv, Linux container, virtual machine or chroot.
You have been warned.

Do not rely on virtualenv details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to support the ``python`` command in the ``commands`` section,
the current environment invocation of ``tox`` creates a fake virtual environment
that just has a symbolic link to the Python executable.
The link is named ``python`` even if the real interpreter's name is different
(such as ``python3.7`` or ``pypy``).
Any other commands are not linked anywhere and it is the users' responsibility
to make sure such commands are in ``$PATH`` and use the correct Python.
This can lead to slightly different results of tests than invoking them directly,
especially if you have assumptions about ``sys.executable`` or other commands
in your tests.

As a specific example, tests should invoke ``python -m pytest`` rather than assuming
the ``pytest`` command is present and uses the correct version of Python.

Don't mix current-env and regular tox runs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tox caches the virtualenvs it creates, and doesn't distinguish between
regular virtualenvs and ``--current-env``.
Don't mix ``tox --current-env`` or ``tox --print-deps-only`` runs
and regular ``tox`` runs (without the flag).
If you ever need to do this, use tox's ``--recreate/-r`` flag to clear the cache.

The plugin should abort with a meaningful error message if this is detected,
but in some cases (such as running ``tox --current-env``, uninstalling the
plugin, and running ``tox``), you will get undefined results
(such as installing packages from PyPI into your current environment).

Environment variables are not passed by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Although the plugin name suggests that current environment is used for tests,
it means the Python environment, not Shell.
If you want the tests to see environment variables of the calling process,
use the ``TOX_TESTENV_PASSENV`` environment variable.
Read `the documentation for passing environment variables to tox
<https://tox.readthedocs.io/en/latest/config.html#conf-passenv>`_.


Other limitations and known bugs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``installed:`` line in the output of ``tox --print-deps-only`` shows irrelevant output
(based on the content of the real or faked virtual environment).

Regardless of any `Python flags <https://docs.python.org/3/using/cmdline.html>`_ used in the shebang of ``tox``,
the tests are invoked with ``sys.executable`` without any added flags
(unless explicitly invoked with them in the ``commands`` section).

The current environment's Python is tested for the major and minor version only.
Different interpreters with the same Python version (such as CPython and PyPy) are treated as equal.

Only Linux is supported, with special emphasis on Fedora.
This plugin might work on other Unix-like systems,
but does not work on Microsoft Windows.

This is alpha quality software.
Use it at your on your own risk.
Pull requests with improvements are welcome.


Development, issues, support
----------------------------

The development happens on GitHub,
at the `fedora-python/tox-current-env <https://github.com/fedora-python/tox-current-env>`_ repository.
You can use the `issue tracker <https://github.com/fedora-python/tox-current-env/issues>`_  there for any discussion
or send Pull Requests.


Tests
~~~~~

In order to run the tests, you'll need ``tox`` and Python 3.6, 3.7 and 3.8 installed.
The integration tests assume all three are available.
On Fedora, you just need to ``dnf install tox``.

Run ``tox`` to invoke the tests.

Running tests of this plugin with its own ``--current-env`` flag will most likely blow up.


License
-------

The ``tox-current-env`` project is licensed under the so-called MIT license, full text available in the `LICENSE <https://github.com/fedora-python/tox-current-env/blob/master/LICENSE>`_ file.


Code of Conduct
---------------

The ``tox-current-env`` project follows the `Fedora's Code of Conduct <https://docs.fedoraproject.org/en-US/project/code-of-conduct/>`_.
