# coding=utf-8
"""Replace core filesystem functions."""

import functools
import glob
import io
import logging
import os
import shutil
import sys
import tarfile
from collections import MutableMapping

import certifi
import rarfile
from six import binary_type, text_type

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

fs_encoding = sys.getfilesystemencoding()


def encode(value):
    """Encode to bytes."""
    return value.encode('utf-8' if os.name != 'nt' else fs_encoding)


def decode(value):
    """Decode to unicode."""
    # on windows the returned info from fs operations needs to be decoded using fs encoding
    return text_type(value, 'utf-8' if os.name != 'nt' else fs_encoding)


def _handle_input(value):
    """Encode argument to utf-8 or fs encoding."""
    # on windows the input params for fs operations needs to be encoded using fs encoding
    return encode(value) if isinstance(value, text_type) else value


def _handle_output(value, target, func):
    """Transform target type using func."""
    if not value:
        return value

    if isinstance(value, target):
        return func(value)

    if isinstance(value, (list, tuple)):
        # Apply arguments for map function
        _handle = functools.partial(_handle_output, target=target, func=func)
        return map(_handle, value)

    if isinstance(value, MutableMapping):
        for k, v in value.items():
            value[k] = _handle_output(v, target, func)
        return value

    return value


def _handle_output_u(value):
    """Convert result to unicode."""
    return _handle_output(value, binary_type, decode)


def _handle_output_b(value):
    """Convert result to binary."""
    return _handle_output(value, text_type, encode)


def _encode_args(*args):
    """Encode var arguments to utf-8 or fs encoding."""
    return [_handle_input(arg) for arg in args]


def _encode_kwargs(**kwargs):
    """Encode var keyword  arguments to utf-8."""
    return {k: _handle_input(arg) for k, arg in kwargs.items()}


def make_closure(f, handle_arg=None, handle_output=None):
    """Apply an input handler and output handler to a function.

    Used to ensure UTF-8 encoding at input and output.
    """
    return patch_output(patch_input(f, handle_arg), handle_output)


def patch_input(f, handle_arg=None):
    """Patch all args and kwargs of function f.

    If handle_arg is None, just return the original function.
    """
    def patched_input(*args, **kwargs):
        return f(*[handle_arg(arg) for arg in args], **{k: handle_arg(arg) for k, arg in kwargs.items()})
    return patched_input if callable(handle_arg) else f


def patch_output(f, handle_output=None):
    """Patch the output of function f with the handle_output function.

    If handle_output is None, just return the original function.
    """
    def patched_output(*args, **kwargs):
        return handle_output(f(*args, **kwargs))
    return patched_output if callable(handle_output) else f


def initialize():
    """Replace original functions if the fs encoding is not utf-8."""
    log.debug('Beginning initializations')
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
        shutil: ['copyfile', 'copymode', 'move', 'rmtree'],
        tarfile: ['is_tarfile'],
        rarfile: ['is_rarfile'],
    }

    # pyOpenSSL 0.14-1 bug: it can't handle unicode input.
    # pyOpenSSL fix -> https://github.com/pyca/pyopenssl/pull/209
    # Our bug: https://github.com/pymedusa/Medusa/issues/1422
    handle_output_map = {
        certifi: _handle_output_b
    }

    if os.name != 'nt':
        affected_functions[os].extend([
            'chmod', 'chown', 'link', 'statvfs', 'symlink'
        ])

    if not fs_encoding or fs_encoding.lower() not in ('utf-8', 'mbcs'):
        handle_input = _handle_input
    else:
        handle_input = None

    for lib, funcs in affected_functions.items():
        handle_output = handle_output_map.get(lib, _handle_output_u)
        for func in funcs:
            msg = 'Patching {pkg.__name__}.{func}'
            log.debug(msg.format(pkg=lib, func=func))
            attr = getattr(lib, func)
            closure = make_closure(attr, handle_input, handle_output)
            setattr(lib, func, closure)
