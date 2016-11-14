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
    _register_utf8_codec()
    _ssl_configuration()
    _configure_mimetypes()
    _handle_old_tornado()
    _unload_system_dogpile()
    _use_shutil_custom()
    _urllib3_disable_warnings()
    _strptime_workaround()
    _configure_guessit()


def _check_python_version():
    if sys.version_info < (2, 7):
        print('Sorry, requires Python 2.7.x')
        sys.exit(1)


def _configure_syspath():
    sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))


def _register_utf8_codec():
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)


def _monkey_patch_fs_functions():
    from . import filesystem
    filesystem.initialize()


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
    """Replace guessit function with a pre-configured one, so guessit.guessit() could be called directly in any place."""
    import guessit
    from ..name_parser.guessit_parser import guessit as pre_configured_guessit
    guessit.guessit = pre_configured_guessit
