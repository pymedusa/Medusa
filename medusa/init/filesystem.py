# coding=utf-8
"""Replace core filesystem functions."""

import glob
import io
import os
import shutil
import sys
import tarfile

from six import binary_type, text_type


def _handle_arg(arg):
    """Encode argument to utf-8."""
    return arg.encode('utf-8') if isinstance(arg, text_type) else arg


def _to_unicode(result):
    """Convert result to unicode."""
    if not result:
        return result

    if isinstance(result, binary_type):
        return text_type(result, 'utf-8')

    if isinstance(result, list) or isinstance(result, tuple):
        return map(_to_unicode, result)

    if isinstance(result, dict):
        for k, v in result.items():
            result[k] = _to_unicode(v)
        return result

    return result


def _varargs(*args):
    """Encode var arguments to utf-8."""
    return [_handle_arg(arg) for arg in args]


def _varkwargs(**kwargs):
    """Encode var keyword  arguments to utf-8."""
    return {k: _handle_arg(arg) for k, arg in kwargs.items()}


def make_closure(f, handle_arg):
    """Create a closure that encodes parameters to utf-8 and call original function."""
    return lambda *args, **kwargs: _to_unicode(f(*[handle_arg(arg) for arg in args], **{k: handle_arg(arg) for k, arg in kwargs.items()}))


def initialize():
    """Replace original functions if the fs encoding is not utf-8."""
    fs_encoding = sys.getfilesystemencoding()
    affected_functions = {
        glob: ['glob'],
        io: ['open'],
        os: ['access', 'chdir', 'listdir', 'makedirs', 'mkdir', 'remove',
             'rename', 'renames', 'rmdir', 'stat', 'unlink', 'utime', 'walk'],
        os.path: ['abspath', 'basename', 'dirname', 'exists', 'getctime', 'getmtime', 'getsize',
                  'isabs', 'isdir', 'isfile', 'join', 'normcase', 'normpath', 'realpath', 'relpath',
                  'split', 'splitext'],
        shutil: ['copyfile', 'copymode', 'move', 'rmtree'],
        tarfile: ['is_tarfile'],
    }

    if os.name != 'nt':
        affected_functions[os].extend(['chmod', 'chown', 'link', 'statvfs', 'symlink'])

    handle_arg = _handle_arg if os.name != 'nt' and (not fs_encoding or fs_encoding.lower() != 'utf-8') else lambda x: x
    for k, v in affected_functions.items():
        for f in v:
            setattr(k, f, make_closure(getattr(k, f), handle_arg))
