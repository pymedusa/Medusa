# coding=utf-8
"""Replace core filesystem functions."""

import glob
import io
import os
import shutil
import sys
import tarfile

import certifi
from six import binary_type, text_type


fs_encoding = sys.getfilesystemencoding()


def encode(value):
    """Encode to bytes."""
    return value.encode('utf-8' if os.name != 'nt' else fs_encoding)


def decode(value):
    """Decode to unicode."""
    # on windows the returned info from fs operations needs to be decoded using fs encoding
    return text_type(value, 'utf-8' if os.name != 'nt' else fs_encoding)


def _handle_input(arg):
    """Encode argument to utf-8 or fs encoding."""
    # on windows the input params for fs operations needs to be encoded using fs encoding
    return encode(arg) if isinstance(arg, text_type) else arg


def _handle_output_u(result):
    """Convert result to unicode."""
    if not result:
        return result

    if isinstance(result, binary_type):
        return decode(result)

    if isinstance(result, list) or isinstance(result, tuple):
        return map(_handle_output_u, result)

    if isinstance(result, dict):
        for k, v in result.items():
            result[k] = _handle_output_u(v)
        return result

    return result


def _handle_output_b(result):
    """Convert result to binary."""
    if not result:
        return result

    if isinstance(result, text_type):
        return encode(result)

    if isinstance(result, list) or isinstance(result, tuple):
        return map(_handle_output_b, result)

    if isinstance(result, dict):
        for k, v in result.items():
            result[k] = _handle_output_b(v)
        return result

    return result


def _varargs(*args):
    """Encode var arguments to utf-8 or fs encoding."""
    return [_handle_input(arg) for arg in args]


def _varkwargs(**kwargs):
    """Encode var keyword  arguments to utf-8."""
    return {k: _handle_input(arg) for k, arg in kwargs.items()}


def make_closure(f, handle_arg, handle_output):
    """Create a closure that encodes parameters to utf-8 and call original function."""
    return lambda *args, **kwargs: handle_output(f(*[handle_arg(arg) for arg in args], **{k: handle_arg(arg) for k, arg in kwargs.items()}))


def initialize():
    """Replace original functions if the fs encoding is not utf-8."""
    if hasattr(sys, '_called_from_test'):
        return

    affected_functions = {
        certifi: ['where', 'old_where'],
        glob: ['glob'],
        io: ['open'],
        os: ['access', 'chdir', 'listdir', 'makedirs', 'mkdir', 'remove',
             'rename', 'renames', 'rmdir', 'stat', 'unlink', 'utime', 'walk'],
        os.path: ['abspath', 'basename', 'dirname', 'exists', 'getctime', 'getmtime', 'getsize',
                  'isabs', 'isdir', 'isfile', 'islink', 'join', 'normcase', 'normpath', 'realpath', 'relpath',
                  'split', 'splitext'],
        shutil: ['copyFile', 'copymode', 'move', 'rmtree'],
        tarfile: ['is_tarfile'],
    }

    # pyOpenSSL 0.14-1 bug: it can't handle unicode input.
    # pyOpenSSL fix -> https://github.com/pyca/pyopenssl/pull/209
    # Our bug: https://github.com/pymedusa/Medusa/issues/1422
    handle_output_map = {
        certifi: _handle_output_b
    }

    if os.name != 'nt':
        affected_functions[os].extend(['chmod', 'chown', 'link', 'statvfs', 'symlink'])

    handle_arg = _handle_input if not fs_encoding or fs_encoding.lower() != 'utf-8' else lambda x: x

    for k, v in affected_functions.items():
        handle_output = handle_output_map.get(k, _handle_output_u)
        for f in v:
            setattr(k, f, make_closure(getattr(k, f), handle_arg, handle_output))
