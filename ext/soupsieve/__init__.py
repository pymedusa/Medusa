"""
Soup Sieve.

A CSS selector filter for BeautifulSoup4.

MIT License

Copyright (c) 2018 Isaac Muse

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import unicode_literals
from .__meta__ import __version__, __version_info__  # noqa: F401
from . import css_parser as cp
from . import css_match as cm
from . import css_types as ct
from .util import DEBUG

__all__ = (
    'SoupSieve', 'compile', 'purge', 'DEBUG',
    'comments', 'icomments', 'closest', 'select', 'select_one',
    'iselect', 'match', 'filter'
)

SoupSieve = cm.SoupSieve


def compile(pattern, namespaces=None, flags=0):  # noqa: A001
    """Compile CSS pattern."""

    if namespaces is None:
        namespaces = ct.Namespaces()
    if not isinstance(namespaces, ct.Namespaces):
        namespaces = ct.Namespaces(**(namespaces))

    if isinstance(pattern, SoupSieve):
        if flags != pattern.flags:
            raise ValueError("Cannot change flags of a pattern")
        elif namespaces != pattern.namespaces:
            raise ValueError("Cannot change namespaces of a pattern")
        return pattern

    return cp._cached_css_compile(pattern, namespaces, flags)


def purge():
    """Purge cached patterns."""

    cp._purge_cache()


def closest(select, tag, namespaces=None, flags=0):
    """Match closest ancestor."""

    return compile(select, namespaces, flags).closest(tag)


def match(select, tag, namespaces=None, flags=0):
    """Match node."""

    return compile(select, namespaces, flags).match(tag)


def filter(select, iterable, namespaces=None, flags=0):  # noqa: A001
    """Filter list of nodes."""

    return compile(select, namespaces, flags).filter(iterable)


def comments(tag, limit=0, flags=0):
    """Get comments only."""

    return list(icomments(tag, limit, flags))


def icomments(tag, limit=0, flags=0):
    """Iterate comments only."""

    for comment in cm.get_comments(tag, limit):
        yield comment


def select_one(select, tag, namespaces=None, flags=0):
    """Select a single tag."""

    return compile(select, namespaces, flags).select_one(tag)


def select(select, tag, namespaces=None, limit=0, flags=0):
    """Select the specified tags."""

    return compile(select, namespaces, flags).select(tag, limit)


def iselect(select, tag, namespaces=None, limit=0, flags=0):
    """Iterate the specified tags."""

    for el in compile(select, namespaces, flags).iselect(tag, limit):
        yield el
