# coding=utf-8
"""Use setup tools to install Medusa."""
import io
import os
import re
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

here = os.path.abspath(os.path.dirname(__file__))


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', 'Arguments to pass into py.test')]

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


def get_app_version():
    """Get the app version from the code."""
    pattern = re.compile(r"VERSION = '([0-9.]+)'")
    filename = os.path.join(here, 'medusa', 'common.py')
    with io.open(filename, 'r', encoding='utf-8') as fh:
        for line in fh:
            match = pattern.match(line)
            if match:
                return match.group(1)

    raise ValueError('Failed to get the app version!')


with open(os.path.join(here, 'readme.md'), 'r') as r:
    long_description = r.read()


def test_install_requires():
    with open(os.path.join(here, 'test_requirements.txt'), 'r') as r:
        return r.read().splitlines(keepends=False)


def packages():
    result = []

    for folder in ('medusa', 'ext', 'lib', 'themes'):
        if os.path.isdir(os.path.join(here, folder)):
            result.append(folder)

    for folder in ('ext2', 'ext3', 'lib2', 'lib3'):
        if os.path.isdir(os.path.join(here, folder)) and sys.version_info.major == int(folder[-1]):
            result.append(folder)

    return result


setup(
    name='pymedusa',
    description='Automatic Video Library Manager for TV Shows',
    version=get_app_version(),
    author='pymedusa team',
    author_email='',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pymedusa/Medusa',
    license='GPLv3',
    packages=packages(),
    include_package_data=True,
    # install_requires=install_requires(),
    extras_require={
        'system-stats': ['psutil'],
    },
    entry_points={
        'console_scripts': [
            'medusa = medusa.__main__:main'
        ]
    },
    cmdclass={'test': PyTest},
    tests_require=test_install_requires(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet',
        'Topic :: Multimedia :: Video',
    ],
)
