# coding=utf-8
"""First modules to initialize."""

import codecs
import datetime
import mimetypes
import os
import shutil
import sys


def initialize():
    """Initialize all fixes and workarounds."""
    _check_python_version()
    _configure_syspath()
    _monkey_patch_fs_functions()
    _monkey_patch_logging_functions()
    _early_basic_logging()
    _register_utf8_codec()
    _ssl_configuration()
    _configure_mimetypes()
    _handle_old_tornado()
    _unload_system_dogpile()
    _use_shutil_custom()
    _urllib3_disable_warnings()
    _strptime_workaround()
    _configure_guessit()
    _configure_subliminal()
    _configure_knowit()


def _check_python_version():
    if sys.version_info < (2, 7):
        print('Sorry, requires Python 2.7.x')
        sys.exit(1)


def _lib_location():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))


def _ext_lib_location():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ext'))


def _configure_syspath():
    sys.path.insert(1, _lib_location())
    sys.path.insert(1, _ext_lib_location())


def _register_utf8_codec():
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)


def _monkey_patch_fs_functions():
    from . import filesystem
    filesystem.initialize()


def _monkey_patch_logging_functions():
    from . import logconfig
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
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("application/sfont", ".otf")
    mimetypes.add_type("application/sfont", ".ttf")
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("application/font-woff", ".woff")
    # Not sure about this one, but we also have halflings in .woff so I think it wont matter
    # mimetypes.add_type("application/font-woff2", ".woff2")


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


def _configure_guessit():
    """Replace guessit with a pre-configured one, so guessit.guessit() could be called directly in any place."""
    import guessit
    from ..name_parser.guessit_parser import guessit as pre_configured_guessit
    guessit.guessit = pre_configured_guessit


def _configure_subliminal():
    """Load subliminal with our custom configuration."""
    from subliminal import provider_manager, refiner_manager

    basename = __name__.split('.')[0]

    # Unregister
    for name in ('legendastv = subliminal.providers.legendastv:LegendasTVProvider',):
        provider_manager.internal_extensions.remove(name)
        provider_manager.registered_extensions.append(name)
        provider_manager.unregister(name)

    # Register
    for name in ('napiprojekt = subliminal.providers.napiprojekt:NapiProjektProvider',
                 'itasa = {basename}.subtitle_providers.itasa:ItaSAProvider'.format(basename=basename),
                 'legendastv = {basename}.subtitle_providers.legendastv:LegendasTVProvider'.format(basename=basename),
                 'wizdom = {basename}.subtitle_providers.wizdom:WizdomProvider'.format(basename=basename)):
        provider_manager.register(name)

    refiner_manager.register('release = {basename}.refiners.release:refine'.format(basename=basename))
    refiner_manager.register('tvepisode = {basename}.refiners.tv_episode:refine'.format(basename=basename))


def _configure_knowit():
    from knowit import api
    from knowit.utils import detect_os

    os_family = detect_os()
    suggested_path = os.path.join(_lib_location(), 'native', os_family)
    if os_family == 'windows':
        subfolder = 'x86_64' if sys.maxsize > 2 ** 32 else 'i386'
        suggested_path = os.path.join(suggested_path, subfolder)

    api.initialize({'mediainfo': suggested_path})
