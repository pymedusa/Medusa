# coding=utf-8
"""Replace core filesystem functions."""

import glob
import io
import os
import shutil
import sys
import tarfile

from six import text_type


def _handle_arg(arg):
    """Encode argument to utf-8."""
    return arg.encode('utf-8') if isinstance(arg, text_type) else arg


def _varargs(*args):
    """Encode var arguments to utf-8."""
    return [_handle_arg(arg) for arg in args]


def _varkwargs(**kwargs):
    """Encode var keyword  arguments to utf-8."""
    return {k: _handle_arg(arg) for k, arg in kwargs.items()}


def make_closure(f):
    """Create a closure that encodes parameters to utf-8 and call original function."""
    return lambda *args, **kwargs: f(*_varargs(*args), **_varkwargs(**kwargs))


def initialize():
    """Replace original functions if the fs encoding is not utf-8."""
    fs_encoding = sys.getfilesystemencoding()
    if os.name != 'nt' and (not fs_encoding or fs_encoding.lower() != 'utf-8'):
        affected_functions = {
            glob: ['glob'],
            io: ['open'],
            os: ['access', 'chdir', 'chmod', 'chown', 'link', 'listdir', 'makedirs', 'mkdir', 'remove',
                 'rename', 'renames', 'rmdir', 'stat', 'statvfs', 'symlink', 'unlink', 'utime', 'walk'],
            os.path: ['abspath', 'basename', 'dirname', 'exists', 'getctime', 'getmtime', 'getsize',
                      'isabs', 'isdir', 'isfile', 'join', 'normcase', 'normpath', 'realpath', 'relpath',
                      'split', 'splitext'],
            shutil: ['copyfile', 'copymode', 'move', 'rmtree'],
            tarfile: ['is_tarfile'],
        }

        for k, v in affected_functions.items():
            for f in v:
                setattr(k, f, make_closure(getattr(k, f)))
