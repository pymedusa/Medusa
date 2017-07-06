"""Setup script for rarfile.
"""

from setuptools import setup

import re

vrx = r"""^__version__ *= *['"]([^'"]+)['"]"""
src = open("rarfile.py").read()
ver = re.search(vrx, src, re.M).group(1)

ldesc = open("README.rst").read().strip()
sdesc = ldesc.split('\n')[0].split(' - ')[1].strip()

setup(
    name = "rarfile",
    version = ver,
    description = sdesc,
    long_description = ldesc,
    author = "Marko Kreen",
    license = "ISC",
    author_email = "markokr@gmail.com",
    url = "https://github.com/markokr/rarfile",
    py_modules = ['rarfile'],
    keywords = ['rar', 'unrar', 'archive'],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Archiving :: Compression",
    ]
)

