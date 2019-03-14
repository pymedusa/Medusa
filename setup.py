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
    install_requires=['tornado==5.1.1', 'six', 'profilehooks', 'contextlib2', ],
    cmdclass={'test': PyTest},
    tests_require=[
        'flake8>=3.5.0',
        'flake8-docstrings>=1.3.0',
        'flake8-import-order>=0.18',
        'flake8-quotes>=1.0.0',
        'pep8-naming>=0.7.0',
        'pycodestyle>=2.4.0',
        'pytest>=4.1.0',
        'pytest-cov>=2.6.1',
        'pytest-flake8>=1.0.2',
        'pytest-tornado5>=2.0.0',
        'PyYAML>=5.1',
        'vcrpy>=2.0.1',
        'mock>=2.0.0',
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
