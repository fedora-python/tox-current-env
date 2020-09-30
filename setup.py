from setuptools import setup, find_packages


def long_description():
    with open("README.rst", encoding="utf-8") as f:
        return f.read()


setup(
    name="tox-current-env",
    description="Use current environment instead of virtualenv for tox testenvs",
    long_description=long_description(),
    author="Miro Hrončok",
    author_email="miro@hroncok.cz",
    url="https://github.com/fedora-python/tox-current-env",
    license="MIT",
    version="0.0.3",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={"tox": ["current-env = tox_current_env.hooks"]},
    install_requires=[
        # We support tox 3.13 only to support Fedora 31.
        # Fedora's tox 3.13 is patched to support Python 3.8 and 3.9,
        # but the one downloaded from PyPI isn't and it doesn't work properly.
        "tox>=3.15; python_version >= '3.8'",
        "tox>=3.13; python_version < '3.8'",
        "importlib_metadata; python_version < '3.8'"
    ],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: tox",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development :: Testing",
    ],
)
