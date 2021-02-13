# coding=utf-8
"""First modules to initialize."""
from __future__ import print_function
from __future__ import unicode_literals

import codecs
import datetime
import mimetypes
import os
import shutil
import site
import sys

from medusa import app


def initialize():
    """Initialize all fixes and workarounds."""
    _check_python_version()
    _configure_syspath()
    # Not working in python3, maybe it's not necessary anymore
    if sys.version_info[0] == 2:
        _monkey_patch_fs_functions()
    _monkey_patch_logging_functions()
    _early_basic_logging()
    _register_utf8_codec()
    _ssl_configuration()
    _configure_mimetypes()
    _handle_old_tornado()
    _unload_system_dogpile()
    # Not working in python3, maybe it's not necessary anymore
    if sys.version_info[0] == 2:
        _use_shutil_custom()
    _urllib3_disable_warnings()
    _strptime_workaround()
    _monkey_patch_bdecode()
    _configure_guessit()
    _configure_subliminal()
    _configure_knowit()
    _configure_unrar()


def _check_python_version():
    if sys.version_info < (2, 7) or (3,) < sys.version_info < (3, 5):
        print('Sorry, requires Python 2.7.x or Python 3.5 and above')
        sys.exit(1)


def _get_lib_location(relative_path):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', relative_path))


def _configure_syspath():
    """Add the vendored libraries into `sys.path`."""
    # Note: These paths will be inserted into `sys.path` in reverse order (LIFO)
    # So the last path on this list will be inserted as the first path on `sys.path`
    # right after the current working dir.
    # For example: [ cwd, pathN, ..., path1, path0, <rest_of_sys.path> ]

    paths_to_insert = [
        _get_lib_location(app.LIB_FOLDER),
        _get_lib_location(app.EXT_FOLDER)
    ]

    if sys.version_info[0] == 2:
        # Add Python 2-only vendored libraries
        paths_to_insert.extend([
            _get_lib_location(app.LIB2_FOLDER),
            _get_lib_location(app.EXT2_FOLDER)
        ])
    elif sys.version_info[0] == 3:
        # Add Python 3-only vendored libraries
        paths_to_insert.extend([
            _get_lib_location(app.LIB3_FOLDER),
            _get_lib_location(app.EXT3_FOLDER)
        ])

    # Insert paths into `sys.path` and handle `.pth` files
    # Inspired by: https://bugs.python.org/issue7744
    for dirpath in paths_to_insert:
        # Clear `sys.path`
        sys.path, remainder = sys.path[:1], sys.path[1:]
        # Add directory as a site-packages directory and handle `.pth` files
        site.addsitedir(dirpath)
        # Restore rest of `sys.path`
        sys.path.extend(remainder)


def _register_utf8_codec():
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)


def _monkey_patch_fs_functions():
    from medusa.init import filesystem
    filesystem.initialize()


def _monkey_patch_logging_functions():
    from medusa.init import logconfig
    logconfig.initialize()


def _early_basic_logging():
    import logging
    logging.basicConfig()


def _ssl_configuration():
    # https://mail.python.org/pipermail/python-dev/2014-September/136300.html
    if sys.version_info >= (2, 7, 9):
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context


def _configure_mimetypes():
    # Fix mimetypes on misconfigured systems
    mimetypes.add_type('text/css', '.css')
    mimetypes.add_type('application/sfont', '.otf')
    mimetypes.add_type('application/sfont', '.ttf')
    mimetypes.add_type('application/javascript', '.js')
    mimetypes.add_type('application/font-woff', '.woff')
    # Not sure about this one, but we also have halflings in .woff so I think it wont matter
    # mimetypes.add_type('application/font-woff2', '.woff2')


def _handle_old_tornado():
    # Do this before application imports, to prevent locked files and incorrect import
    old_tornado = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tornado'))
    if os.path.isdir(old_tornado):
        shutil.move(old_tornado, old_tornado + '_kill')
        shutil.rmtree(old_tornado + '_kill')


def _unload_system_dogpile():
    # An issue found on synology DSM makes the dogpile module from the system to be always loaded before
    # sys.path is changed. # That causes the application to fail to start because that version is old and some submodules are not found.
    # http://stackoverflow.com/questions/2918898/prevent-python-from-caching-the-imported-modules
    try:
        if 'dogpile' in sys.modules:
            del sys.modules['dogpile']
    except AttributeError:
        pass


def _use_shutil_custom():
    import shutil_custom
    shutil.copyfile = shutil_custom.copyfile_custom


def _urllib3_disable_warnings():
    import requests
    requests.packages.urllib3.disable_warnings()


def _strptime_workaround():
    # http://bugs.python.org/issue7980#msg221094
    datetime.datetime.strptime('20110101', '%Y%m%d')


def _monkey_patch_bdecode():
    """
    Monkeypatch `bencodepy` to add an option to allow extra data, and change the default parameters.

    This allows us to not raise an exception if bencoded data contains extra data after valid prefix.
    """
    import bencodepy
    import bencodepy.compat

    class CustomBencodeDecoder(bencodepy.BencodeDecoder):
        def decode(self, value, allow_extra_data=False):
            try:
                value = bencodepy.compat.to_binary(value)
                data, length = self.decode_func[value[0:1]](value, 0)
            except (IndexError, KeyError, TypeError, ValueError):
                raise bencodepy.BencodeDecodeError('not a valid bencoded string')

            if length != len(value) and not allow_extra_data:
                raise bencodepy.BencodeDecodeError('invalid bencoded value (data after valid prefix)')

            return data

    class CustomBencode(bencodepy.Bencode):
        def __init__(self, encoding=None, encoding_fallback=None, dict_ordered=False, dict_ordered_sort=False):
            self.decoder = CustomBencodeDecoder(
                encoding=encoding,
                encoding_fallback=encoding_fallback,
                dict_ordered=dict_ordered,
                dict_ordered_sort=dict_ordered_sort,
            )
            self.encoder = bencodepy.BencodeEncoder()

        def decode(self, value, allow_extra_data=False):
            return self.decoder.decode(value, allow_extra_data=allow_extra_data)

    # Replace the default encoder
    bencodepy.DEFAULT = CustomBencode(encoding='utf-8', encoding_fallback='value')


def _configure_guessit():
    """Replace guessit with a pre-configured one, so guessit.guessit() could be called directly in any place."""
    import guessit
    from medusa.name_parser.guessit_parser import (
        guessit as pre_configured_guessit,
    )
    guessit.guessit = pre_configured_guessit


def _configure_subliminal():
    """Load subliminal with our custom configuration."""
    from subliminal import provider_manager, refiner_manager

    basename = __name__.split('.')[0]

    # Unregister
    # for name in ('legendastv = subliminal.providers.legendastv:LegendasTVProvider',):
    #    provider_manager.internal_extensions.remove(name)
    #    provider_manager.registered_extensions.append(name)
    #    provider_manager.unregister(name)

    # Register
    for name in ('napiprojekt = subliminal.providers.napiprojekt:NapiProjektProvider',
                 'subtitulamos = {basename}.subtitle_providers.subtitulamos:SubtitulamosProvider'.format(basename=basename),
                 'wizdom = {basename}.subtitle_providers.wizdom:WizdomProvider'.format(basename=basename)):
        provider_manager.register(name)

    refiner_manager.register('release = {basename}.refiners.release:refine'.format(basename=basename))
    refiner_manager.register('tvepisode = {basename}.refiners.tv_episode:refine'.format(basename=basename))


def _configure_knowit():
    from knowit import api
    from knowit.utils import detect_os

    os_family = detect_os()
    suggested_path = os.path.join(_get_lib_location(app.LIB_FOLDER), 'native', os_family)
    if os_family == 'windows':
        subfolder = 'x86_64' if sys.maxsize > 2 ** 32 else 'i386'
        suggested_path = os.path.join(suggested_path, subfolder)

    api.initialize({'mediainfo': suggested_path})


def _configure_unrar():
    from knowit.utils import detect_os
    import rarfile

    os_family = detect_os()
    suggested_path = os.path.join(_get_lib_location(app.LIB_FOLDER), 'native', os_family)
    if os_family == 'windows':
        unrar_path = os.path.join(suggested_path, 'UnRAR.exe')
        rarfile.UNRAR_TOOL = unrar_path
