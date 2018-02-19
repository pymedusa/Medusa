# coding=utf-8
"""First modules to initialize."""

import codecs
import collections
import datetime
import logging
import mimetypes
import os
import shutil
import sys

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def initialize():
    """Initialize all fixes and workarounds."""
    log.debug('Beginning initializations')
    _check_python_version()
    _early_basic_logging()
    _strptime_workaround()
    _register_utf8_codec()
    _configure_syspath()
    _unload_system_dogpile()
    _use_shutil_custom()
    _monkey_patch_fs_functions()
    # configuration
    _configure_mimetypes()
    _configure_ssl()
    _configure_guessit()
    _configure_subliminal()
    _configure_knowit()
    log.debug('Finished initializations')


def _check_python_version():
    log.debug('Checking python version: {}'.format(sys.version))
    if sys.version_info < (2, 7):
        sys.exit('Sorry, requires Python 2.7.x')


def _root_location():
    here = os.path.dirname(__file__)
    root = os.path.join(here, '..', '..')
    abs_root = os.path.abspath(root)
    return abs_root


def _pkg_location(root):
    return os.path.join(root, 'pkgs')


def _custom_pkg_locatoin(root):
    return os.path.join(root, 'custom')


def _common_pkg_location(root):
    return os.path.join(root, 'common')


def _py_version_specific_packages(root, version):
    return os.path.join(root, 'py{0}'.format(version))


def _configure_syspath():
    root = _root_location()
    log.debug('Project root location: {}'.format(root))
    pkg_root = _pkg_location(root)
    log.debug('Package root location: {}'.format(pkg_root))

    py_ver = sys.version_info
    major_ver_pkgs = _py_version_specific_packages(pkg_root, py_ver.major)

    pkgs = collections.OrderedDict()
    pkgs['Custom'] = _custom_pkg_locatoin(pkg_root)
    pkgs['Common'] = _common_pkg_location(pkg_root)
    pkgs['Python version specific'] = major_ver_pkgs

    log.debug('Initial sys.path = {}'.format(sys.path))
    log.debug('Inserting libs')
    for pkg, loc in pkgs.items():
        log.debug('{name} package location: {dir}'.format(name=pkg, dir=loc))
        sys.path.insert(1, loc)
    log.debug('Current sys.path = {}'.format(sys.path))


def _register_utf8_codec():
    def _register_utf8(value):
        if value.lower() == 'cp65001':
            utf8 = codecs.lookup('utf-8')
            log.debug('Registering {}'.format(utf8))
            return utf8
    log.debug('Registering codecs')
    codecs.register(_register_utf8)


def _monkey_patch_fs_functions():
    from medusa.init import filesystem
    filesystem.initialize()


def _early_basic_logging():
    import logging
    logging.basicConfig()


def _configure_ssl():
    # https://mail.python.org/pipermail/python-dev/2014-September/136300.html
    if sys.version_info >= (2, 7, 9):
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context


def _configure_mimetypes():
    # Fix mimetypes on misconfigured systems
    fixes = {
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.otf': 'application/sfont',
        '.ttf': 'application/sfont',
        '.woff': 'application/font-woff',
        '.woff2': 'application/font-woff2',
    }
    for extension, mimetype in fixes.items():
        mimetypes.add_type(mimetype, extension)


def _unload_modules(name):
    log.debug('Checking if {module} is loaded'.format(module=name))
    if name in sys.modules:
        log.debug('{module} is loaded; attempting to remove it')
        del sys.modules[name]
        log.debug('{module} removed')


def _unload_system_dogpile():
    # An issue found on Synology DSM makes the dogpile module from the system
    # always load before sys.path is changed causing the application to fail
    # to start because that version is old and some submodules are not found.
    # prevent
    # http://stackoverflow.com/questions/2918898
    _unload_modules('dogpile')


def _use_shutil_custom():
    import shutil_custom
    shutil.copyfile = shutil_custom.copyfile_custom


def _strptime_workaround():
    # http://bugs.python.org/issue7980#msg221094
    datetime.datetime.strptime('20110101', '%Y%m%d')


def _configure_guessit():
    """Replace guessit with a pre-configured one, so guessit.guessit() could be called directly in any place."""
    import guessit
    from medusa.name_parser.guessit_parser import (
        guessit as pre_configured_guessit,
    )
    guessit.guessit = pre_configured_guessit


def _configure_subliminal():
    """Load subliminal with our custom configuration."""
    log.debug('Configuring subliminal')

    try:
        from subliminal import provider_manager, refiner_manager
    except ImportError:
        log.warning('Subliminal not available!'
                    ' Subtitles will not be donwloaded')
        return

    base = __name__.split('.')[0]
    application = '{base}.subtitles'.format(base=base)

    provider_config = {
        'subliminal': {
            'napiprojekt': 'napiprojekt:NapiProjektProvider',
        },
        application: {
            'itasa': 'itasa:ItaSAProvider',
            'wizdom': 'wizdom:WizdomProvider',
        }
    }

    refiner_config = {
        application: {
            'release': 'release:refine',
            'tvepisode': 'tv_episode:refine',
        }
    }

    def configure(category, config, manager):
        for source, items in config.items():
            for name, item in items.items():
                msg = 'Registering {type} from {source}: {name}'
                log.info(msg.format(type=category, source=source, name=name))
                entry_point = '{name} = {source}.{category}s.{item}'.format(
                    name=name, source=source, category=category,
                    item=item.format(base=source),
                )
                manager.register(entry_point)

    configure('provider', provider_config, provider_manager)
    configure('refiner', refiner_config, refiner_manager)


def _configure_knowit():
    from knowit import api
    from knowit.utils import detect_os

    log.debug('Configuring knowit')

    os_family = detect_os()
    root = _root_location()
    pkg_root = _pkg_location(root)
    custom = _custom_pkg_locatoin(pkg_root)
    suggested_path = os.path.join(custom, 'native', os_family)
    if os_family == 'windows':
        subfolder = 'x86_64' if sys.maxsize > 2 ** 32 else 'i386'
        suggested_path = os.path.join(suggested_path, subfolder)

    api.initialize({'mediainfo': suggested_path})
