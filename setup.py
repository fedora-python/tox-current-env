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
    version="0.0.14",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={"tox": ["current-env = tox_current_env.hooks"]},
    install_requires=[
        "tox>=3.28",
        "importlib_metadata; python_version < '3.8'"
    ],
    extras_require={
        "tests": [
            "pytest",
            "pytest-xdist",
            "packaging",
        ],
    },
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
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development :: Testing",
    ],
)
