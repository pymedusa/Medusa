"""
Use setup tools to install Medusa
"""
import os
from setuptools import find_packages, setup

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__)))

with open(os.path.join(ROOT, 'readme.md'), 'r') as r:
    long_description = r.read()

setup(
    name="medusa",
    description="Automatic Video Library Manager for TV Shows",
    long_description=long_description,
    packages=find_packages(),
    install_requires=['six', 'profilehooks', 'contextlib2', 'gi', ],
    test_suite="tests",
    tests_require=[
        'coveralls',
        'flake8_docstrings',
        'flake8-import-order',
        'pytest',
        'pytest-cov',
        'pytest-flake8',
        'pytest-tornado',
        'PyYAML',
        'pep8-naming ',
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
