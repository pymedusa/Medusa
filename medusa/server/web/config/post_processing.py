# coding=utf-8

"""Configure Post Processing."""

from __future__ import unicode_literals

import os

from medusa import (
    app,
    config,
    logger,
    naming,
    ui,
)
from medusa.helper.exceptions import ex
from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

import rarfile

from tornroutes import route


@route('/config/postProcessing(/?.*)')
class ConfigPostProcessing(Config):
    """Handler for Post Processing configuration."""

    def __init__(self, *args, **kwargs):
        """Initialize handler."""
        super(ConfigPostProcessing, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the Post Processing configuration page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()

    def savePostProcessing(self, process_automatically=None, unpack=None, allowed_extensions=None,
                           tv_download_dir=None, naming_pattern=None, naming_multi_ep=None,
                           naming_anime=None, naming_abd_pattern=None, naming_sports_pattern=None,
                           naming_anime_pattern=None, naming_anime_multi_ep=None,
                           autopostprocessor_frequency=None):
        """[deprecated] Save Post Processing configuration."""
        # @TODO: The following validations need to be incorporated into API v2 (PATCH /api/v2/config/main)

        results = []

        if not config.change_TV_DOWNLOAD_DIR(tv_download_dir):
            results += ['Unable to create directory {dir}, '
                        'dir not changed.'.format(dir=os.path.normpath(tv_download_dir))]

        config.change_AUTOPOSTPROCESSOR_FREQUENCY(autopostprocessor_frequency)
        config.change_PROCESS_AUTOMATICALLY(process_automatically)

        if unpack:
            if self.is_rar_supported():
                app.UNPACK = config.checkbox_to_value(unpack)
            else:
                app.UNPACK = 0
                results.append('Unpacking Not Supported, disabling unpack setting')
        else:
            app.UNPACK = config.checkbox_to_value(unpack)

        # @TODO: postprocessor for `POSTPONE_IF_NO_SUBS` and `ALLOWED_EXTENSIONS` ?
        # If 'postpone if no subs' is enabled, we must have SRT in allowed extensions list
        if app.POSTPONE_IF_NO_SUBS:
            allowed_extensions += ',srt'
            # # Auto PP must be disabled because FINDSUBTITLE thread that calls manual PP (like nzbtomedia)
            # app.PROCESS_AUTOMATICALLY = 0

        if self.isNamingValid(naming_pattern, naming_multi_ep, anime_type=naming_anime) != 'invalid':
            app.NAMING_PATTERN = naming_pattern
            app.NAMING_MULTI_EP = int(naming_multi_ep)
            app.NAMING_ANIME = int(naming_anime)
            app.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()
        else:
            if int(naming_anime) in [1, 2]:
                results.append('You tried saving an invalid anime naming config, not saving your naming settings')
            else:
                results.append('You tried saving an invalid naming config, not saving your naming settings')

        if self.isNamingValid(naming_anime_pattern, naming_anime_multi_ep, anime_type=naming_anime) != 'invalid':
            app.NAMING_ANIME_PATTERN = naming_anime_pattern
            app.NAMING_ANIME_MULTI_EP = int(naming_anime_multi_ep)
            app.NAMING_ANIME = int(naming_anime)
            app.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()
        else:
            if int(naming_anime) in [1, 2]:
                results.append('You tried saving an invalid anime naming config, not saving your naming settings')
            else:
                results.append('You tried saving an invalid naming config, not saving your naming settings')

        if self.isNamingValid(naming_abd_pattern, None, abd=True) != 'invalid':
            app.NAMING_ABD_PATTERN = naming_abd_pattern
        else:
            results.append(
                'You tried saving an invalid air-by-date naming config, not saving your air-by-date settings')

        if self.isNamingValid(naming_sports_pattern, None, sports=True) != 'invalid':
            app.NAMING_SPORTS_PATTERN = naming_sports_pattern
        else:
            results.append(
                'You tried saving an invalid sports naming config, not saving your sports settings')

        app.instance.save_config()

        if results:
            for x in results:
                logger.log(x, logger.WARNING)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', os.path.join(app.CONFIG_FILE))

        return self.redirect('/config/postProcessing/')

    @staticmethod
    def testNaming(pattern=None, multi=None, abd=False, sports=False, anime_type=None):
        """Test episode naming pattern."""
        if multi is not None:
            multi = int(multi)

        if anime_type is not None:
            anime_type = int(anime_type)

        result = naming.test_name(pattern, multi, abd, sports, anime_type)

        result = os.path.join(result['dir'], result['name'])

        return result

    @staticmethod
    def isNamingValid(pattern=None, multi=None, abd=False, sports=False, anime_type=None):
        """Validate episode naming pattern."""
        if pattern is None:
            return 'invalid'

        if multi is not None:
            multi = int(multi)

        if anime_type is not None:
            anime_type = int(anime_type)

        # air by date shows just need one check, we don't need to worry about season folders
        if abd:
            is_valid = naming.check_valid_abd_naming(pattern)
            require_season_folders = False

        # sport shows just need one check, we don't need to worry about season folders
        elif sports:
            is_valid = naming.check_valid_sports_naming(pattern)
            require_season_folders = False

        else:
            # check validity of single and multi ep cases for the whole path
            is_valid = naming.check_valid_naming(pattern, multi, anime_type)

            # check validity of single and multi ep cases for only the file name
            require_season_folders = naming.check_force_season_folders(pattern, multi, anime_type)

        if is_valid and not require_season_folders:
            return 'valid'
        elif is_valid and require_season_folders:
            return 'seasonfolders'
        else:
            return 'invalid'

    @staticmethod
    def is_rar_supported():
        """Check rar unpacking support."""
        try:
            rarfile.custom_check([rarfile.UNRAR_TOOL], True)
        except rarfile.RarExecError:
            logger.log('UNRAR tool not available.', logger.WARNING)
            return False
        except Exception as msg:
            logger.log('Rar Not Supported: {error}'.format(error=ex(msg)), logger.ERROR)
            return False
        return True
