"""Base theme module."""
from __future__ import unicode_literals

import io
import json
import logging
import os

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Theme(object):
    """Base theme class."""

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.version = kwargs.get('version')
        self.dep_version = kwargs.get('depVersion')
        self.author = kwargs.get('author')


def read_themes():
    """Read the theme folder and create a Theme object for every entry, if valid."""
    themes = []
    theme_root = os.path.join(app.PROG_DIR, 'themes')
    themes_from_fs = [os.path.join(theme_root, theme_dir) for theme_dir in os.listdir(theme_root)
                      if os.path.isdir(os.path.join(theme_root, theme_dir))]
    for theme_path in themes_from_fs:
        # validate the directory structure
        try:
            package_json = validate_theme(theme_path)
        except Exception as error:
            log.error('Error reading theme {theme}, {error!r}', {'theme': theme_path, 'error': error})
            raise Exception('Error in one of the theme paths. Please fix the error and start medusa.')

        if not package_json:
            log.debug('Skipping reading theme {theme}, as the folder is empty', {'theme': theme_path})
            continue

        # create a theme object from the `package.json` data
        themes.append(Theme(**package_json))

    return themes


def validate_theme(theme_path):
    """Validate theme configuration."""
    try:
        dir_list = os.listdir(theme_path)
    except Exception as err:
        raise Exception('Unable to list directories in {path}: {err!r}'.format(path=theme_path, err=err))

    # If the folder is completely empty, then the theme was probably removed, so just skip it
    if not dir_list:
        return False

    if not os.path.isdir(os.path.join(theme_path, 'assets')):
        raise Exception('Missing assets folder. Please refer to the medusa theming documentation.')

    for check_folder in ('css', 'js', 'img'):
        if not os.path.isdir(os.path.join(theme_path, 'assets', check_folder)):
            raise Exception('Missing folder: [theme]/assets/{check_folder}. '
                            'Please refer to the medusa theming documentation.'.format(check_folder=check_folder))

    try:
        with io.open(os.path.join(theme_path, 'package.json'), 'r', encoding='utf-8') as pj:
            package_json = json.load(pj)
    except IOError:
        raise Exception('Cannot read package.json. Please refer to the medusa theming documentation.')

    # Validate if they mandatory keys are configured in the package.json.
    if not package_json.get('name') or not package_json.get('version'):
        raise Exception("As a bare minimum you'll need at least to provide the 'name' and and 'version' key. "
                        'Please refer to the medusa theming documentation.')

    if (not os.path.isdir(os.path.join(theme_path, 'templates')) and
            not os.path.isfile(os.path.join(theme_path, 'index.html'))):
        raise Exception('You need to have at least a templates folder with mako temnplates, '
                        "or an index.html in your [theme's] root. Please refer to the medusa theming documentation.")

    return package_json
