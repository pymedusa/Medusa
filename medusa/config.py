# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>

#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

import datetime
import os.path
import re

from requests.compat import urlsplit
from six import iteritems
from six.moves.urllib.parse import urlunsplit, uses_netloc
from . import app, common, db, helpers, logger, naming
from .helper.common import try_int

# Address poor support for scgi over unix domain sockets
# this is not nicely handled by python currently
# http://bugs.python.org/issue23636
uses_netloc.append('scgi')

naming_ep_type = ("%(seasonnumber)dx%(episodenumber)02d",
                  "s%(seasonnumber)02de%(episodenumber)02d",
                  "S%(seasonnumber)02dE%(episodenumber)02d",
                  "%(seasonnumber)02dx%(episodenumber)02d")

sports_ep_type = ("%(seasonnumber)dx%(episodenumber)02d",
                  "s%(seasonnumber)02de%(episodenumber)02d",
                  "S%(seasonnumber)02dE%(episodenumber)02d",
                  "%(seasonnumber)02dx%(episodenumber)02d")

naming_ep_type_text = ("1x02", "s01e02", "S01E02", "01x02")

naming_multi_ep_type = {0: ["-%(episodenumber)02d"] * len(naming_ep_type),
                        1: [" - " + x for x in naming_ep_type],
                        2: [x + "%(episodenumber)02d" for x in ("x", "e", "E", "x")]}
naming_multi_ep_type_text = ("extend", "duplicate", "repeat")

naming_sep_type = (" - ", " ")
naming_sep_type_text = (" - ", "space")


def change_HTTPS_CERT(https_cert):
    """
    Replace HTTPS Certificate file path

    :param https_cert: path to the new certificate file
    :return: True on success, False on failure
    """
    if https_cert == '':
        app.HTTPS_CERT = ''
        return True

    if os.path.normpath(app.HTTPS_CERT) != os.path.normpath(https_cert):
        if helpers.make_dir(os.path.dirname(os.path.abspath(https_cert))):
            app.HTTPS_CERT = os.path.normpath(https_cert)
            logger.log(u"Changed https cert path to " + https_cert)
        else:
            return False

    return True


def change_HTTPS_KEY(https_key):
    """
    Replace HTTPS Key file path

    :param https_key: path to the new key file
    :return: True on success, False on failure
    """
    if https_key == '':
        app.HTTPS_KEY = ''
        return True

    if os.path.normpath(app.HTTPS_KEY) != os.path.normpath(https_key):
        if helpers.make_dir(os.path.dirname(os.path.abspath(https_key))):
            app.HTTPS_KEY = os.path.normpath(https_key)
            logger.log(u"Changed https key path to " + https_key)
        else:
            return False

    return True


def change_LOG_DIR(log_dir):
    """
    Change logging directory for application and webserver

    :param log_dir: Path to new logging directory
    :return: True on success, False on failure
    """
    abs_log_dir = os.path.normpath(os.path.join(app.DATA_DIR, log_dir))

    if os.path.normpath(app.LOG_DIR) != abs_log_dir:
        if not helpers.make_dir(abs_log_dir):
            return False

        app.ACTUAL_LOG_DIR = os.path.normpath(log_dir)
        app.LOG_DIR = abs_log_dir

    return True


def change_NZB_DIR(nzb_dir):
    """
    Change NZB Folder

    :param nzb_dir: New NZB Folder location
    :return: True on success, False on failure
    """
    if nzb_dir == '':
        app.NZB_DIR = ''
        return True

    if os.path.normpath(app.NZB_DIR) != os.path.normpath(nzb_dir):
        if helpers.make_dir(nzb_dir):
            app.NZB_DIR = os.path.normpath(nzb_dir)
            logger.log(u"Changed NZB folder to " + nzb_dir)
        else:
            return False

    return True


def change_TORRENT_DIR(torrent_dir):
    """
    Change torrent directory

    :param torrent_dir: New torrent directory
    :return: True on success, False on failure
    """
    if torrent_dir == '':
        app.TORRENT_DIR = ''
        return True

    if os.path.normpath(app.TORRENT_DIR) != os.path.normpath(torrent_dir):
        if helpers.make_dir(torrent_dir):
            app.TORRENT_DIR = os.path.normpath(torrent_dir)
            logger.log(u"Changed torrent folder to " + torrent_dir)
        else:
            return False

    return True


def change_TV_DOWNLOAD_DIR(tv_download_dir):
    """
    Change TV_DOWNLOAD directory (used by postprocessor)

    :param tv_download_dir: New tv download directory
    :return: True on success, False on failure
    """
    if tv_download_dir == '':
        app.TV_DOWNLOAD_DIR = ''
        return True

    if os.path.normpath(app.TV_DOWNLOAD_DIR) != os.path.normpath(tv_download_dir):
        if helpers.make_dir(tv_download_dir):
            app.TV_DOWNLOAD_DIR = os.path.normpath(tv_download_dir)
            logger.log(u"Changed TV download folder to " + tv_download_dir)
        else:
            return False

    return True


def change_AUTOPOSTPROCESSOR_FREQUENCY(freq):
    """
    Change frequency of automatic postprocessing thread
    TODO: Make all thread frequency changers in config.py return True/False status

    :param freq: New frequency
    """
    app.AUTOPOSTPROCESSOR_FREQUENCY = try_int(freq, app.DEFAULT_AUTOPOSTPROCESSOR_FREQUENCY)

    if app.AUTOPOSTPROCESSOR_FREQUENCY < app.MIN_AUTOPOSTPROCESSOR_FREQUENCY:
        app.AUTOPOSTPROCESSOR_FREQUENCY = app.MIN_AUTOPOSTPROCESSOR_FREQUENCY

    app.autoPostProcessorScheduler.cycleTime = datetime.timedelta(minutes=app.AUTOPOSTPROCESSOR_FREQUENCY)


def change_DAILYSEARCH_FREQUENCY(freq):
    """
    Change frequency of daily search thread

    :param freq: New frequency
    """
    app.DAILYSEARCH_FREQUENCY = try_int(freq, app.DEFAULT_DAILYSEARCH_FREQUENCY)

    if app.DAILYSEARCH_FREQUENCY < app.MIN_DAILYSEARCH_FREQUENCY:
        app.DAILYSEARCH_FREQUENCY = app.MIN_DAILYSEARCH_FREQUENCY

    app.dailySearchScheduler.cycleTime = datetime.timedelta(minutes=app.DAILYSEARCH_FREQUENCY)


def change_BACKLOG_FREQUENCY(freq):
    """
    Change frequency of backlog thread

    :param freq: New frequency
    """
    app.BACKLOG_FREQUENCY = try_int(freq, app.DEFAULT_BACKLOG_FREQUENCY)

    app.MIN_BACKLOG_FREQUENCY = app.instance.get_backlog_cycle_time()
    if app.BACKLOG_FREQUENCY < app.MIN_BACKLOG_FREQUENCY:
        app.BACKLOG_FREQUENCY = app.MIN_BACKLOG_FREQUENCY

    app.backlogSearchScheduler.cycleTime = datetime.timedelta(minutes=app.BACKLOG_FREQUENCY)


def change_UPDATE_FREQUENCY(freq):
    """
    Change frequency of daily updater thread

    :param freq: New frequency
    """
    app.UPDATE_FREQUENCY = try_int(freq, app.DEFAULT_UPDATE_FREQUENCY)

    if app.UPDATE_FREQUENCY < app.MIN_UPDATE_FREQUENCY:
        app.UPDATE_FREQUENCY = app.MIN_UPDATE_FREQUENCY

    app.versionCheckScheduler.cycleTime = datetime.timedelta(hours=app.UPDATE_FREQUENCY)


def change_SHOWUPDATE_HOUR(freq):
    """
    Change frequency of show updater thread

    :param freq: New frequency
    """
    app.SHOWUPDATE_HOUR = try_int(freq, app.DEFAULT_SHOWUPDATE_HOUR)

    if app.SHOWUPDATE_HOUR > 23:
        app.SHOWUPDATE_HOUR = 0
    elif app.SHOWUPDATE_HOUR < 0:
        app.SHOWUPDATE_HOUR = 0

    app.showUpdateScheduler.start_time = datetime.time(hour=app.SHOWUPDATE_HOUR)


def change_SUBTITLES_FINDER_FREQUENCY(subtitles_finder_frequency):
    """
    Change frequency of subtitle thread

    :param subtitles_finder_frequency: New frequency
    """
    if subtitles_finder_frequency == '' or subtitles_finder_frequency is None:
        subtitles_finder_frequency = 1

    app.SUBTITLES_FINDER_FREQUENCY = try_int(subtitles_finder_frequency, 1)


def change_VERSION_NOTIFY(version_notify):
    """
    Change frequency of versioncheck thread

    :param version_notify: New frequency
    """
    oldSetting = app.VERSION_NOTIFY

    app.VERSION_NOTIFY = version_notify

    if not version_notify:
        app.NEWEST_VERSION_STRING = None

    if oldSetting is False and version_notify is True:
        app.versionCheckScheduler.forceRun()


def change_DOWNLOAD_PROPERS(download_propers):
    """
    Enable/Disable proper download thread
    TODO: Make this return True/False on success/failure

    :param download_propers: New desired state
    """
    download_propers = checkbox_to_value(download_propers)

    if app.DOWNLOAD_PROPERS == download_propers:
        return

    app.DOWNLOAD_PROPERS = download_propers
    if app.DOWNLOAD_PROPERS:
        if not app.properFinderScheduler.enable:
            logger.log(u"Starting PROPERFINDER thread", logger.INFO)
            app.properFinderScheduler.silent = False
            app.properFinderScheduler.enable = True
        else:
            logger.log(u"Unable to start PROPERFINDER thread. Already running", logger.INFO)
    else:
        app.properFinderScheduler.enable = False
        app.traktCheckerScheduler.silent = True
        logger.log(u"Stopping PROPERFINDER thread", logger.INFO)


def change_USE_TRAKT(use_trakt):
    """
    Enable/disable trakt thread
    TODO: Make this return true/false on success/failure

    :param use_trakt: New desired state
    """
    use_trakt = checkbox_to_value(use_trakt)

    if app.USE_TRAKT == use_trakt:
        return

    app.USE_TRAKT = use_trakt
    if app.USE_TRAKT:
        if not app.traktCheckerScheduler.enable:
            logger.log(u"Starting TRAKTCHECKER thread", logger.INFO)
            app.traktCheckerScheduler.silent = False
            app.traktCheckerScheduler.enable = True
        else:
            logger.log(u"Unable to start TRAKTCHECKER thread. Already running", logger.INFO)
    else:
        app.traktCheckerScheduler.enable = False
        app.traktCheckerScheduler.silent = True
        logger.log(u"Stopping TRAKTCHECKER thread", logger.INFO)


def change_USE_SUBTITLES(use_subtitles):
    """
    Enable/Disable subtitle searcher
    TODO: Make this return true/false on success/failure

    :param use_subtitles: New desired state
    """
    use_subtitles = checkbox_to_value(use_subtitles)

    if app.USE_SUBTITLES == use_subtitles:
        return

    app.USE_SUBTITLES = use_subtitles
    if app.USE_SUBTITLES:
        if not app.subtitlesFinderScheduler.enable:
            logger.log(u"Starting SUBTITLESFINDER thread", logger.INFO)
            app.subtitlesFinderScheduler.silent = False
            app.subtitlesFinderScheduler.enable = True
        else:
            logger.log(u"Unable to start SUBTITLESFINDER thread. Already running", logger.INFO)
    else:
        app.subtitlesFinderScheduler.enable = False
        app.subtitlesFinderScheduler.silent = True
        logger.log(u"Stopping SUBTITLESFINDER thread", logger.INFO)


def change_PROCESS_AUTOMATICALLY(process_automatically):
    """
    Enable/Disable postprocessor thread
    TODO: Make this return True/False on success/failure

    :param process_automatically: New desired state
    """
    process_automatically = checkbox_to_value(process_automatically)

    if app.PROCESS_AUTOMATICALLY == process_automatically:
        return

    app.PROCESS_AUTOMATICALLY = process_automatically
    if app.PROCESS_AUTOMATICALLY:
        if not app.autoPostProcessorScheduler.enable:
            logger.log(u"Starting POSTPROCESSOR thread", logger.INFO)
            app.autoPostProcessorScheduler.silent = False
            app.autoPostProcessorScheduler.enable = True
        else:
            logger.log(u"Unable to start POSTPROCESSOR thread. Already running", logger.INFO)
    else:
        logger.log(u"Stopping POSTPROCESSOR thread", logger.INFO)
        app.autoPostProcessorScheduler.enable = False
        app.autoPostProcessorScheduler.silent = True


def CheckSection(CFG, sec):
    """ Check if INI section exists, if not create it """

    if sec in CFG:
        return True

    CFG[sec] = {}
    return False


def checkbox_to_value(option, value_on=1, value_off=0):
    """
    Turns checkbox option 'on' or 'true' to value_on (1)
    any other value returns value_off (0)
    """

    if isinstance(option, list):
        option = option[-1]

    if option in ('on', 'true'):
        return value_on

    return value_off


def clean_host(host, default_port=None):
    """
    Returns host or host:port or empty string from a given url or host
    If no port is found and default_port is given use host:default_port
    """

    host = host.strip()

    if host:

        match_host_port = re.search(r'(?:http.*://)?(?P<host>[^:/]+).?(?P<port>[0-9]*).*', host)

        cleaned_host = match_host_port.group('host')
        cleaned_port = match_host_port.group('port')

        if cleaned_host:

            if cleaned_port:
                host = cleaned_host + ':' + cleaned_port

            elif default_port:
                host = cleaned_host + ':' + str(default_port)

            else:
                host = cleaned_host

        else:
            host = ''

    return host


def clean_hosts(hosts, default_port=None):
    """
    Returns list of cleaned hosts by clean_host

    :param hosts: list of hosts
    :param default_port: default port to use
    :return: list of cleaned hosts
    """
    cleaned_hosts = []

    for cur_host in [host.strip() for host in hosts.split(",") if host.strip()]:
        cleaned_host = clean_host(cur_host, default_port)
        if cleaned_host:
            cleaned_hosts.append(cleaned_host)

    cleaned_hosts = ",".join(cleaned_hosts) if cleaned_hosts else ''

    return cleaned_hosts


def clean_url(url):
    """
    Returns an cleaned url starting with a scheme and folder with trailing /
    or an empty string
    """

    if url and url.strip():

        url = url.strip()

        if '://' not in url:
            url = '//' + url

        scheme, netloc, path, query, fragment = urlsplit(url, 'http')

        if not path:
            path += '/'

        cleaned_url = urlunsplit((scheme, netloc, path, query, fragment))

    else:
        cleaned_url = ''

    return cleaned_url


################################################################################
# Check_setting_int                                                            #
################################################################################
def minimax(val, default, low, high):
    """ Return value forced within range """

    val = try_int(val, default)

    if val < low:
        return low
    if val > high:
        return high

    return val


################################################################################
# Check_setting_int                                                            #
################################################################################
def check_setting_int(config, cfg_name, item_name, def_val, silent=True):
    try:
        my_val = config[cfg_name][item_name]
        if str(my_val).lower() == "true":
            my_val = 1
        elif str(my_val).lower() == "false":
            my_val = 0

        my_val = int(my_val)

        if str(my_val) == str(None):
            raise Exception
    except Exception:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except Exception:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if not silent:
        logger.log(item_name + " -> " + str(my_val), logger.DEBUG)

    return my_val


################################################################################
# Check_setting_bool                                                           #
################################################################################
def check_setting_bool(config, cfg_name, item_name, def_val, silent=True):
    return bool(check_setting_int(config=config, cfg_name=cfg_name, item_name=item_name, def_val=def_val, silent=silent))


################################################################################
# Check_setting_float                                                          #
################################################################################
def check_setting_float(config, cfg_name, item_name, def_val, silent=True):
    try:
        my_val = float(config[cfg_name][item_name])
        if str(my_val) == str(None):
            raise Exception
    except Exception:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except Exception:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if not silent:
        logger.log(item_name + " -> " + str(my_val), logger.DEBUG)

    return my_val


################################################################################
# Check_setting_str                                                            #
################################################################################
def check_setting_str(config, cfg_name, item_name, def_val, silent=True, censor_log=False, valid_values=None):
    # For passwords you must include the word `password` in the item_name and add `helpers.encrypt(ITEM_NAME, ENCRYPTION_VERSION)` in save_config()
    if not censor_log:
        censor_level = common.privacy_levels['stupid']
    else:
        censor_level = common.privacy_levels[censor_log]
    privacy_level = common.privacy_levels[app.PRIVACY_LEVEL]
    if bool(item_name.find('password') + 1):
        encryption_version = app.ENCRYPTION_VERSION
    else:
        encryption_version = 0

    try:
        my_val = helpers.decrypt(config[cfg_name][item_name], encryption_version)
        if str(my_val) == str(None):
            raise Exception
    except Exception:
        my_val = def_val
        try:
            config[cfg_name][item_name] = helpers.encrypt(my_val, encryption_version)
        except Exception:
            config[cfg_name] = {}
            config[cfg_name][item_name] = helpers.encrypt(my_val, encryption_version)

    if privacy_level >= censor_level or (cfg_name, item_name) in iteritems(logger.censored_items):
        if not item_name.endswith('custom_url'):
            logger.censored_items[cfg_name, item_name] = my_val
            logger.rebuild_censored_list()

    if not silent:
        logger.log(item_name + " -> " + my_val, logger.DEBUG)

    if valid_values and my_val not in valid_values:
        return def_val

    return my_val


################################################################################
# Check_setting                                                                #
################################################################################
def check_setting(config, section, attr_type, attr, default=None, silent=True, **kwargs):
    """
    Check setting from config file
    """
    func = {
        'string': check_setting_str,
        'int': check_setting_int,
        'float': check_setting_float,
        'bool': check_setting_bool,
    }
    return func[attr_type](config, section, attr, default, silent, **kwargs)


################################################################################
# Check_setting                                                                #
################################################################################
def check_provider_setting(config, provider, attr_type, attr, default=None, silent=True, **kwargs):
    """
    Check setting from config file
    """
    name = provider.get_id()
    section = name.upper()
    attr = '{name}_{attr}'.format(name=name, attr=attr)
    return check_setting(config, section, attr_type, attr, default, silent, **kwargs)


################################################################################
# Load Provider Setting                                                        #
################################################################################
def load_provider_setting(config, provider, attr_type, attr, default=None, silent=True, **kwargs):
    if hasattr(provider, attr):
        value = check_provider_setting(config, provider, attr_type, attr, default, silent, **kwargs)
        setattr(provider, attr, value)


################################################################################
# Load Provider Setting                                                        #
################################################################################
def save_provider_setting(config, provider, attr, **kwargs):
    if hasattr(provider, attr):
        section = kwargs.pop('section', provider.get_id().upper())
        setting = '{name}_{attr}'.format(name=provider.get_id(), attr=attr)
        value = kwargs.pop('value', getattr(provider, attr))
        if value in [True, False]:
            value = int(value)
        config[section][setting] = value


class ConfigMigrator(object):
    def __init__(self, config_obj):
        """
        Initializes a config migrator that can take the config from the version indicated in the config
        file up to the version required by SB
        """

        self.config_obj = config_obj

        # check the version of the config
        self.config_version = check_setting_int(config_obj, 'General', 'config_version', app.CONFIG_VERSION)
        self.expected_config_version = app.CONFIG_VERSION
        self.migration_names = {
            1: 'Custom naming',
            2: 'Sync backup number with version number',
            3: 'Rename omgwtfnzb variables',
            4: 'Add newznab cat_ids',
            5: 'Metadata update',
            6: 'Convert from XBMC to new KODI variables',
            7: 'Use version 2 for password encryption',
            8: 'Convert Plex setting keys'
        }

    def migrate_config(self):
        """
        Calls each successive migration until the config is the same version as SB expects
        """

        if self.config_version > self.expected_config_version:
            logger.log_error_and_exit(
                u"""Your config version (%i) has been incremented past what this version of the application supports (%i).
                If you have used other forks or a newer version of the application, your config file may be unusable due to their modifications.""" %
                (self.config_version, self.expected_config_version)
            )

        app.CONFIG_VERSION = self.config_version

        while self.config_version < self.expected_config_version:
            next_version = self.config_version + 1

            if next_version in self.migration_names:
                migration_name = ': ' + self.migration_names[next_version]
            else:
                migration_name = ''

            logger.log(u"Backing up config before upgrade")
            if not helpers.backup_versioned_file(app.CONFIG_FILE, self.config_version):
                logger.log_error_and_exit(u"Config backup failed, abort upgrading config")
            else:
                logger.log(u"Proceeding with upgrade")

            # do the migration, expect a method named _migrate_v<num>
            logger.log(u"Migrating config up to version " + str(next_version) + migration_name)
            getattr(self, '_migrate_v' + str(next_version))()
            self.config_version = next_version

            # save new config after migration
            app.CONFIG_VERSION = self.config_version
            logger.log(u"Saving config file to disk")
            app.instance.save_config()

    # Migration v1: Custom naming
    def _migrate_v1(self):
        """
        Reads in the old naming settings from your config and generates a new config template from them.
        """

        app.NAMING_PATTERN = self._name_to_pattern()
        logger.log(u"Based on your old settings I'm setting your new naming pattern to: " + app.NAMING_PATTERN)

        app.NAMING_CUSTOM_ABD = bool(check_setting_int(self.config_obj, 'General', 'naming_dates', 0))

        if app.NAMING_CUSTOM_ABD:
            app.NAMING_ABD_PATTERN = self._name_to_pattern(True)
            logger.log(u"Adding a custom air-by-date naming pattern to your config: " + app.NAMING_ABD_PATTERN)
        else:
            app.NAMING_ABD_PATTERN = naming.name_abd_presets[0]

        app.NAMING_MULTI_EP = int(check_setting_int(self.config_obj, 'General', 'naming_multi_ep_type', 1))

        # see if any of their shows used season folders
        main_db_con = db.DBConnection()
        season_folder_shows = main_db_con.select("SELECT indexer_id FROM tv_shows WHERE flatten_folders = 0 LIMIT 1")

        # if any shows had season folders on then prepend season folder to the pattern
        if season_folder_shows:

            old_season_format = check_setting_str(self.config_obj, 'General', 'season_folders_format', 'Season %02d')

            if old_season_format:
                try:
                    new_season_format = old_season_format % 9
                    new_season_format = str(new_season_format).replace('09', '%0S')
                    new_season_format = new_season_format.replace('9', '%S')

                    logger.log(
                        u"Changed season folder format from " + old_season_format + " to " + new_season_format + ", prepending it to your naming config")
                    app.NAMING_PATTERN = new_season_format + os.sep + app.NAMING_PATTERN

                except (TypeError, ValueError):
                    logger.log(u"Can't change " + old_season_format + " to new season format", logger.ERROR)

        # if no shows had it on then don't flatten any shows and don't put season folders in the config
        else:

            logger.log(u"No shows were using season folders before so I'm disabling flattening on all shows")

            # don't flatten any shows at all
            main_db_con.action("UPDATE tv_shows SET flatten_folders = 0")

        app.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()

    def _name_to_pattern(self, abd=False):

        # get the old settings from the file
        use_periods = bool(check_setting_int(self.config_obj, 'General', 'naming_use_periods', 0))
        ep_type = check_setting_int(self.config_obj, 'General', 'naming_ep_type', 0)
        sep_type = check_setting_int(self.config_obj, 'General', 'naming_sep_type', 0)
        use_quality = bool(check_setting_int(self.config_obj, 'General', 'naming_quality', 0))

        use_show_name = bool(check_setting_int(self.config_obj, 'General', 'naming_show_name', 1))
        use_ep_name = bool(check_setting_int(self.config_obj, 'General', 'naming_ep_name', 1))

        # make the presets into templates
        naming_ep_type = ("%Sx%0E",
                          "s%0Se%0E",
                          "S%0SE%0E",
                          "%0Sx%0E")

        # set up our data to use
        if use_periods:
            show_name = '%S.N'
            ep_name = '%E.N'
            ep_quality = '%Q.N'
            abd_string = '%A.D'
        else:
            show_name = '%SN'
            ep_name = '%EN'
            ep_quality = '%QN'
            abd_string = '%A-D'

        if abd and abd_string:
            ep_string = abd_string
        else:
            ep_string = naming_ep_type[ep_type]

        finalName = ""

        # start with the show name
        if use_show_name and show_name:
            finalName += show_name + naming_sep_type[sep_type]

        # add the season/ep stuff
        finalName += ep_string

        # add the episode name
        if use_ep_name and ep_name:
            finalName += naming_sep_type[sep_type] + ep_name

        # add the quality
        if use_quality and ep_quality:
            finalName += naming_sep_type[sep_type] + ep_quality

        if use_periods:
            finalName = re.sub(r"\s+", ".", finalName)

        return finalName

    # Migration v2: Dummy migration to sync backup number with config version number
    def _migrate_v2(self):
        return

    # Migration v2: Rename omgwtfnzb variables
    def _migrate_v3(self):
        """
        Reads in the old naming settings from your config and generates a new config template from them.
        """
        # get the old settings from the file and store them in the new variable names
        app.OMGWTFNZBS_USERNAME = check_setting_str(self.config_obj, 'omgwtfnzbs', 'omgwtfnzbs_uid', '')
        app.OMGWTFNZBS_APIKEY = check_setting_str(self.config_obj, 'omgwtfnzbs', 'omgwtfnzbs_key', '')

    # Migration v4: Add default newznab cat_ids
    def _migrate_v4(self):
        """ Update newznab providers so that the category IDs can be set independently via the config """

        new_newznab_data = []
        old_newznab_data = check_setting_str(self.config_obj, 'Newznab', 'newznab_data', '')

        if old_newznab_data:
            old_newznab_data_list = old_newznab_data.split("!!!")

            for cur_provider_data in old_newznab_data_list:
                try:
                    name, url, key, enabled = cur_provider_data.split("|")
                except ValueError:
                    logger.log(u"Skipping Newznab provider string: '" + cur_provider_data + "', incorrect format",
                               logger.ERROR)
                    continue

                if name == 'Sick Beard Index':
                    key = '0'

                if name == 'NZBs.org':
                    cat_ids = '5030,5040,5060,5070,5090'
                else:
                    cat_ids = '5030,5040,5060'

                cur_provider_data_list = [name, url, key, cat_ids, enabled]
                new_newznab_data.append("|".join(cur_provider_data_list))

            app.NEWZNAB_DATA = "!!!".join(new_newznab_data)

    # Migration v5: Metadata upgrade
    def _migrate_v5(self):
        """Updates metadata values to the new format.

        Quick overview of what the upgrade does:

        new | old | description (new)
        ----+-----+--------------------
          1 |  1  | show metadata
          2 |  2  | episode metadata
          3 |  4  | show fanart
          4 |  3  | show poster
          5 |  -  | show banner
          6 |  5  | episode thumb
          7 |  6  | season poster
          8 |  -  | season banner
          9 |  -  | season all poster
         10 |  -  | season all banner

        Note that the ini places start at 1 while the list index starts at 0.
        old format: 0|0|0|0|0|0 -- 6 places
        new format: 0|0|0|0|0|0|0|0|0|0 -- 10 places

        Drop the use of use_banner option.
        Migrate the poster override to just using the banner option (applies to xbmc only).
        """

        metadata_xbmc = check_setting_str(self.config_obj, 'General', 'metadata_xbmc', '0|0|0|0|0|0')
        metadata_xbmc_12plus = check_setting_str(self.config_obj, 'General', 'metadata_xbmc_12plus', '0|0|0|0|0|0')
        metadata_mediabrowser = check_setting_str(self.config_obj, 'General', 'metadata_mediabrowser', '0|0|0|0|0|0')
        metadata_ps3 = check_setting_str(self.config_obj, 'General', 'metadata_ps3', '0|0|0|0|0|0')
        metadata_wdtv = check_setting_str(self.config_obj, 'General', 'metadata_wdtv', '0|0|0|0|0|0')
        metadata_tivo = check_setting_str(self.config_obj, 'General', 'metadata_tivo', '0|0|0|0|0|0')
        metadata_mede8er = check_setting_str(self.config_obj, 'General', 'metadata_mede8er', '0|0|0|0|0|0')

        use_banner = bool(check_setting_int(self.config_obj, 'General', 'use_banner', 0))

        def _migrate_metadata(metadata, metadata_name, use_banner):
            cur_metadata = metadata.split('|')
            # if target has the old number of values, do upgrade
            if len(cur_metadata) == 6:
                logger.log(u"Upgrading " + metadata_name + " metadata, old value: " + metadata)
                cur_metadata.insert(4, '0')
                cur_metadata.append('0')
                cur_metadata.append('0')
                cur_metadata.append('0')
                # swap show fanart, show poster
                cur_metadata[3], cur_metadata[2] = cur_metadata[2], cur_metadata[3]
                # if user was using use_banner to override the poster, instead enable the banner option and deactivate poster
                if metadata_name == 'XBMC' and use_banner:
                    cur_metadata[4], cur_metadata[3] = cur_metadata[3], '0'
                # write new format
                metadata = '|'.join(cur_metadata)
                logger.log(u"Upgrading " + metadata_name + " metadata, new value: " + metadata)

            elif len(cur_metadata) == 10:

                metadata = '|'.join(cur_metadata)
                logger.log(u"Keeping " + metadata_name + " metadata, value: " + metadata)

            else:
                logger.log(u"Skipping " + metadata_name + " metadata: '" + metadata + "', incorrect format",
                           logger.ERROR)
                metadata = '0|0|0|0|0|0|0|0|0|0'
                logger.log(u"Setting " + metadata_name + " metadata, new value: " + metadata)

            return metadata

        app.METADATA_XBMC = _migrate_metadata(metadata_xbmc, 'XBMC', use_banner)
        app.METADATA_XBMC_12PLUS = _migrate_metadata(metadata_xbmc_12plus, 'XBMC 12+', use_banner)
        app.METADATA_MEDIABROWSER = _migrate_metadata(metadata_mediabrowser, 'MediaBrowser', use_banner)
        app.METADATA_PS3 = _migrate_metadata(metadata_ps3, 'PS3', use_banner)
        app.METADATA_WDTV = _migrate_metadata(metadata_wdtv, 'WDTV', use_banner)
        app.METADATA_TIVO = _migrate_metadata(metadata_tivo, 'TIVO', use_banner)
        app.METADATA_MEDE8ER = _migrate_metadata(metadata_mede8er, 'Mede8er', use_banner)

    # Migration v6: Convert from XBMC to KODI variables
    def _migrate_v6(self):
        app.USE_KODI = bool(check_setting_int(self.config_obj, 'XBMC', 'use_xbmc', 0))
        app.KODI_ALWAYS_ON = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_always_on', 1))
        app.KODI_NOTIFY_ONSNATCH = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_notify_onsnatch', 0))
        app.KODI_NOTIFY_ONDOWNLOAD = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_notify_ondownload', 0))
        app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_notify_onsubtitledownload', 0))
        app.KODI_UPDATE_LIBRARY = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_update_library', 0))
        app.KODI_UPDATE_FULL = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_update_full', 0))
        app.KODI_UPDATE_ONLYFIRST = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_update_onlyfirst', 0))
        app.KODI_HOST = check_setting_str(self.config_obj, 'XBMC', 'xbmc_host', '')
        app.KODI_USERNAME = check_setting_str(self.config_obj, 'XBMC', 'xbmc_username', '', censor_log=True)
        app.KODI_PASSWORD = check_setting_str(self.config_obj, 'XBMC', 'xbmc_password', '', censor_log=True)
        app.METADATA_KODI = check_setting_str(self.config_obj, 'General', 'metadata_xbmc', '0|0|0|0|0|0|0|0|0|0')
        app.METADATA_KODI_12PLUS = check_setting_str(self.config_obj, 'General', 'metadata_xbmc_12plus', '0|0|0|0|0|0|0|0|0|0')

    # Migration v6: Use version 2 for password encryption
    def _migrate_v7(self):
        app.ENCRYPTION_VERSION = 2

    def _migrate_v8(self):
        app.PLEX_CLIENT_HOST = check_setting_str(self.config_obj, 'Plex', 'plex_host', '')
        app.PLEX_SERVER_USERNAME = check_setting_str(self.config_obj, 'Plex', 'plex_username', '', censor_log=True)
        app.PLEX_SERVER_PASSWORD = check_setting_str(self.config_obj, 'Plex', 'plex_password', '', censor_log=True)
        app.USE_PLEX_SERVER = bool(check_setting_int(self.config_obj, 'Plex', 'use_plex', 0))

    def _migrate_v9(self):
        """
        Migrate to config version 9
        """
        # Added setting "enable_manualsearch" for providers (dynamic setting)
        pass
