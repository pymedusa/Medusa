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

from tornroutes import route

from unrar2 import RarFile


@route('/config/postProcessing(/?.*)')
class ConfigPostProcessing(Config):
    """
    Handler for Post Processor configuration
    """
    def __init__(self, *args, **kwargs):
        super(ConfigPostProcessing, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the Post Processor configuration page
        """
        t = PageTemplate(rh=self, filename='config_postProcessing.mako')

        return t.render(submenu=self.ConfigMenu(),
                        controller='config', action='postProcessing')

    def savePostProcessing(self, kodi_data=None, kodi_12plus_data=None,
                           mediabrowser_data=None, sony_ps3_data=None,
                           wdtv_data=None, tivo_data=None, mede8er_data=None,
                           keep_processed_dir=None, process_method=None,
                           del_rar_contents=None, process_automatically=None,
                           no_delete=None, rename_episodes=None, airdate_episodes=None,
                           file_timestamp_timezone=None, unpack=None,
                           move_associated_files=None, sync_files=None,
                           postpone_if_sync_files=None, postpone_if_no_subs=None,
                           allowed_extensions=None, tv_download_dir=None,
                           create_missing_show_dirs=None, add_shows_wo_dir=None,
                           extra_scripts=None, nfo_rename=None,
                           naming_pattern=None, naming_multi_ep=None,
                           naming_custom_abd=None, naming_anime=None,
                           naming_abd_pattern=None, naming_strip_year=None,
                           naming_custom_sports=None, naming_sports_pattern=None,
                           naming_custom_anime=None, naming_anime_pattern=None,
                           naming_anime_multi_ep=None, autopostprocessor_frequency=None):

        results = []

        if not config.change_TV_DOWNLOAD_DIR(tv_download_dir):
            results += ['Unable to create directory {dir}, '
                        'dir not changed.'.format(dir=os.path.normpath(tv_download_dir))]

        config.change_AUTOPOSTPROCESSOR_FREQUENCY(autopostprocessor_frequency)
        config.change_PROCESS_AUTOMATICALLY(process_automatically)

        if unpack:
            if self.isRarSupported() != 'not supported':
                app.UNPACK = config.checkbox_to_value(unpack)
            else:
                app.UNPACK = 0
                results.append('Unpacking Not Supported, disabling unpack setting')
        else:
            app.UNPACK = config.checkbox_to_value(unpack)
        app.NO_DELETE = config.checkbox_to_value(no_delete)
        app.KEEP_PROCESSED_DIR = config.checkbox_to_value(keep_processed_dir)
        app.CREATE_MISSING_SHOW_DIRS = config.checkbox_to_value(create_missing_show_dirs)
        app.ADD_SHOWS_WO_DIR = config.checkbox_to_value(add_shows_wo_dir)
        app.PROCESS_METHOD = process_method
        app.DELRARCONTENTS = config.checkbox_to_value(del_rar_contents)
        app.EXTRA_SCRIPTS = [_.strip() for _ in extra_scripts.split('|') if _.strip()]
        app.RENAME_EPISODES = config.checkbox_to_value(rename_episodes)
        app.AIRDATE_EPISODES = config.checkbox_to_value(airdate_episodes)
        app.FILE_TIMESTAMP_TIMEZONE = file_timestamp_timezone
        app.MOVE_ASSOCIATED_FILES = config.checkbox_to_value(move_associated_files)
        app.SYNC_FILES = [_.strip() for _ in sync_files.split(',') if _.strip()]
        app.POSTPONE_IF_SYNC_FILES = config.checkbox_to_value(postpone_if_sync_files)
        app.POSTPONE_IF_NO_SUBS = config.checkbox_to_value(postpone_if_no_subs)
        # If 'postpone if no subs' is enabled, we must have SRT in allowed extensions list
        if app.POSTPONE_IF_NO_SUBS:
            allowed_extensions += ',srt'
            # # Auto PP must be disabled because FINDSUBTITLE thread that calls manual PP (like nzbtomedia)
            # app.PROCESS_AUTOMATICALLY = 0
        app.ALLOWED_EXTENSIONS = {_.strip() for _ in allowed_extensions.split(',') if _.strip()}
        app.NAMING_CUSTOM_ABD = config.checkbox_to_value(naming_custom_abd)
        app.NAMING_CUSTOM_SPORTS = config.checkbox_to_value(naming_custom_sports)
        app.NAMING_CUSTOM_ANIME = config.checkbox_to_value(naming_custom_anime)
        app.NAMING_STRIP_YEAR = config.checkbox_to_value(naming_strip_year)
        app.NFO_RENAME = config.checkbox_to_value(nfo_rename)

        app.METADATA_KODI = kodi_data.split('|')
        app.METADATA_KODI_12PLUS = kodi_12plus_data.split('|')
        app.METADATA_MEDIABROWSER = mediabrowser_data.split('|')
        app.METADATA_PS3 = sony_ps3_data.split('|')
        app.METADATA_WDTV = wdtv_data.split('|')
        app.METADATA_TIVO = tivo_data.split('|')
        app.METADATA_MEDE8ER = mede8er_data.split('|')

        app.metadata_provider_dict['KODI'].set_config(app.METADATA_KODI)
        app.metadata_provider_dict['KODI 12+'].set_config(app.METADATA_KODI_12PLUS)
        app.metadata_provider_dict['MediaBrowser'].set_config(app.METADATA_MEDIABROWSER)
        app.metadata_provider_dict['Sony PS3'].set_config(app.METADATA_PS3)
        app.metadata_provider_dict['WDTV'].set_config(app.METADATA_WDTV)
        app.metadata_provider_dict['TIVO'].set_config(app.METADATA_TIVO)
        app.metadata_provider_dict['Mede8er'].set_config(app.METADATA_MEDE8ER)

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
        """
        Test episode naming pattern
        """

        if multi is not None:
            multi = int(multi)

        if anime_type is not None:
            anime_type = int(anime_type)

        result = naming.test_name(pattern, multi, abd, sports, anime_type)

        result = os.path.join(result['dir'], result['name'])

        return result

    @staticmethod
    def isNamingValid(pattern=None, multi=None, abd=False, sports=False, anime_type=None):
        """
        Validate episode naming pattern
        """
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
    def isRarSupported():
        """
        Test Packing Support:
            - Simulating in memory rar extraction on test.rar file
        """

        try:
            rar_path = os.path.join(app.PROG_DIR, 'lib', 'unrar2', 'test.rar')
            testing = RarFile(rar_path).read_files('*test.txt')
            if testing[0][1] == 'This is only a test.':
                return 'supported'
            logger.log('Rar Not Supported: Can not read the content of test file', logger.ERROR)
            return 'not supported'
        except Exception as msg:
            logger.log('Rar Not Supported: {error}'.format(error=ex(msg)), logger.ERROR)
            return 'not supported'
