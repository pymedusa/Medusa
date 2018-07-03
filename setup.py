"""Use setup tools to install Medusa."""
import os
import sys

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand

here = os.path.abspath(os.path.dirname(__file__))


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass into py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest

        errno = pytest.main(self.pytest_args.split(' '))
        sys.exit(errno)


with open(os.path.join(here, 'readme.md'), 'r') as r:
    long_description = r.read()

setup(
    name="medusa",
    description="Automatic Video Library Manager for TV Shows",
    long_description=long_description,
    packages=find_packages(),
    install_requires=['tornado==5.0.2', 'six', 'profilehooks', 'contextlib2', ],
    cmdclass={'test': PyTest},
    tests_require=[
        'dredd_hooks',
        'flake8',
        'flake8-docstrings',
        'flake8-import-order',
        'pep8-naming',
        'pycodestyle==2.3.1',
        'pytest',
        'pytest-cov',
        'pytest-flake8==0.9.1',
        'pytest-tornado5',
        'PyYAML<4',
        'mock',
    ],
    extras_require={
        'system-stats': ['psutil'],
    },
    classifiers=[
        'Development Status :: ???',
        'Intended Audience :: Developers',
        'Operating System :: POSIC :: LINUX',
        'Topic :: ???',
    ],
)
