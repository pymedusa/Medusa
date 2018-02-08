"""Base theme module."""
import json
import logging
import os
from medusa import app
from medusa.logger.adapters.style import BraceAdapter


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

themes = []


class Theme(object):
    """Base theme class."""

    def __init__(self, **kwargs):
        self.name = kwargs.get('baseName')
        self.version = kwargs.get('version')
        self.package_name = kwargs.get('name')
        self.dep_version = kwargs.get('depVersion')
        self.author = kwargs.get('author')


def read_themes():
    """Read the theme folder and create a Theme object for every entry, if valid."""
    theme_root = os.path.join(app.PROG_DIR, 'themes')
    themes_from_fs = [os.path.join(theme_root, theme_dir) for theme_dir in os.listdir(theme_root) if os.path.isdir(os.path.join(theme_root, theme_dir))]
    for theme_path in themes_from_fs:
        # validate the directory structure
        try:
            validate_theme(theme_path)
        except Exception as error:
            log.error('Error reading theme {theme}, {error!r}', {'theme': theme_path, 'error': error})
            raise Exception('Error in one of the theme paths. Please fix the error and start medusa.')

        # validate the package.json
        package_json = json.load(open(os.path.join(theme_path, 'package.json')))
        if theme_path:
            package_json['baseName'] = os.path.basename(os.path.normpath(theme_path))
            themes.append(Theme(**package_json))

    return themes


def validate_theme(theme_path):
    """Validate theme configuration."""
    if not os.path.isdir(os.path.join(theme_path, 'assets')):
        raise Exception('Missing assets folder. Please refer to the medusa theming documentation.')

    for check_folder in ('css', 'js', 'img'):
        if not os.path.isdir(os.path.join(theme_path, 'assets', check_folder)):
            raise Exception('Missing folder: [theme]/assets/{check_folder}. '
                            'Please refer to the medusa theming documentation.'.format(check_folder=check_folder))

    try:
        package_json = json.load(open(os.path.join(theme_path, 'package.json')))
    except IOError:
        raise Exception('Cannot read package.json. Please refer to the medusa theming documentation.')

    # Validate if they mandatory keys are configured in the package.json.
    if not package_json.get('name') or not package_json.get('version'):
        raise Exception("As a bare minimum you'l need at least to provide the 'name' and and 'version' key. "
                        "Please refer to the medusa theming documentation.")

    if not os.path.isdir(os.path.join(theme_path, 'templates')) and not os.path.isfile(os.path.join(theme_path, 'index.html')):
        raise Exception("You need to have at least a templates folder with mako temnplates, "
                        "or an index.html in your [theme's] root. Please refer to the medusa theming documentation.")

    return True
