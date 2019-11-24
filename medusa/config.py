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

from __future__ import unicode_literals

import datetime
import logging
import os.path
import re
from builtins import object
from builtins import str

from contextlib2 import suppress

from medusa import app, common, db, helpers, logger, naming, scheduler
from medusa.helper.common import try_int
from medusa.helpers.utils import split_and_strip
from medusa.logger.adapters.style import BraceAdapter
from medusa.updater.version_checker import CheckVersion

from requests.compat import urlsplit

from six import iteritems, string_types, text_type
from six.moves.urllib.parse import urlunsplit, uses_netloc

from tornado.web import StaticFileHandler

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

# Address poor support for scgi over unix domain sockets
# this is not nicely handled by python currently
# http://bugs.python.org/issue23636
uses_netloc.append('scgi')

naming_ep_type = ('%(seasonnumber)dx%(episodenumber)02d',
                  's%(seasonnumber)02de%(episodenumber)02d',
                  'S%(seasonnumber)02dE%(episodenumber)02d',
                  '%(seasonnumber)02dx%(episodenumber)02d')

sports_ep_type = ('%(seasonnumber)dx%(episodenumber)02d',
                  's%(seasonnumber)02de%(episodenumber)02d',
                  'S%(seasonnumber)02dE%(episodenumber)02d',
                  '%(seasonnumber)02dx%(episodenumber)02d')

naming_ep_type_text = ('1x02', 's01e02', 'S01E02', '01x02')

naming_multi_ep_type = {0: ['-%(episodenumber)02d'] * len(naming_ep_type),
                        1: [' - ' + x for x in naming_ep_type],
                        2: [x + '%(episodenumber)02d' for x in ('x', 'e', 'E', 'x')]}
naming_multi_ep_type_text = ('extend', 'duplicate', 'repeat')

naming_sep_type = (' - ', ' ')
naming_sep_type_text = (' - ', 'space')


def change_HTTPS_CERT(https_cert):
    """
    Replace HTTPS Certificate file path.

    :param https_cert: path to the new certificate file
    :return: True on success, False on failure
    """
    if https_cert == '':
        app.HTTPS_CERT = ''
        return True

    if os.path.normpath(app.HTTPS_CERT) != os.path.normpath(https_cert):
        if helpers.make_dir(os.path.dirname(os.path.abspath(https_cert))):
            app.HTTPS_CERT = os.path.normpath(https_cert)
            log.info(u'Changed https cert path to {cert_path}', {u'cert_path': https_cert})
        else:
            return False

    return True


def change_HTTPS_KEY(https_key):
    """
    Replace HTTPS Key file path.

    :param https_key: path to the new key file
    :return: True on success, False on failure
    """
    if https_key == '':
        app.HTTPS_KEY = ''
        return True

    if os.path.normpath(app.HTTPS_KEY) != os.path.normpath(https_key):
        if helpers.make_dir(os.path.dirname(os.path.abspath(https_key))):
            app.HTTPS_KEY = os.path.normpath(https_key)
            log.info(u'Changed https key path to {key_path}', {u'key_path': https_key})
        else:
            return False

    return True


def change_LOG_DIR(log_dir):
    """
    Change logging directory for application and webserver.

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
            log.info(u'Changed NZB folder to {nzb_dir}', {'nzb_dir': nzb_dir})
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
            log.info(u'Changed torrent folder to {torrent_dir}', {u'torrent_dir': torrent_dir})
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
            log.info(u'Changed TV download folder to {tv_download_dir}', {u'tv_download_dir': tv_download_dir})
        else:
            return False

    return True


def change_AUTOPOSTPROCESSOR_FREQUENCY(freq):
    """
    Change frequency of automatic postprocessing thread
    TODO: Make all thread frequency changers in config.py return True/False status

    :param freq: New frequency
    """
    app.AUTOPOSTPROCESSOR_FREQUENCY = try_int(freq, 10)

    if app.AUTOPOSTPROCESSOR_FREQUENCY < app.MIN_AUTOPOSTPROCESSOR_FREQUENCY:
        app.AUTOPOSTPROCESSOR_FREQUENCY = app.MIN_AUTOPOSTPROCESSOR_FREQUENCY

    app.post_processor_scheduler.cycleTime = datetime.timedelta(minutes=app.AUTOPOSTPROCESSOR_FREQUENCY)


def change_TORRENT_CHECKER_FREQUENCY(freq):
    """
    Change frequency of Torrent Checker thread

    :param freq: New frequency
    """
    app.TORRENT_CHECKER_FREQUECY = try_int(freq, app.DEFAULT_TORRENT_CHECKER_FREQUENCY)

    if app.TORRENT_CHECKER_FREQUECY < app.MIN_TORRENT_CHECKER_FREQUENCY:
        app.TORRENT_CHECKER_FREQUECY = app.MIN_TORRENT_CHECKER_FREQUENCY

    app.torrent_checker_scheduler.cycleTime = datetime.timedelta(minutes=app.TORRENT_CHECKER_FREQUECY)


def change_DAILYSEARCH_FREQUENCY(freq):
    """
    Change frequency of daily search thread

    :param freq: New frequency
    """
    app.DAILYSEARCH_FREQUENCY = try_int(freq, app.DEFAULT_DAILYSEARCH_FREQUENCY)

    if app.DAILYSEARCH_FREQUENCY < app.MIN_DAILYSEARCH_FREQUENCY:
        app.DAILYSEARCH_FREQUENCY = app.MIN_DAILYSEARCH_FREQUENCY

    app.daily_search_scheduler.cycleTime = datetime.timedelta(minutes=app.DAILYSEARCH_FREQUENCY)


def change_BACKLOG_FREQUENCY(freq):
    """
    Change frequency of backlog thread

    :param freq: New frequency
    """
    app.BACKLOG_FREQUENCY = try_int(freq, app.DEFAULT_BACKLOG_FREQUENCY)

    app.MIN_BACKLOG_FREQUENCY = app.instance.get_backlog_cycle_time()
    if app.BACKLOG_FREQUENCY < app.MIN_BACKLOG_FREQUENCY:
        app.BACKLOG_FREQUENCY = app.MIN_BACKLOG_FREQUENCY

    app.backlog_search_scheduler.cycleTime = datetime.timedelta(minutes=app.BACKLOG_FREQUENCY)


def change_PROPERS_FREQUENCY(check_propers_interval):
    """
    Change frequency of backlog thread

    :param freq: New frequency
    """
    if not app.DOWNLOAD_PROPERS:
        return

    if app.CHECK_PROPERS_INTERVAL == check_propers_interval:
        return

    if check_propers_interval in app.PROPERS_SEARCH_INTERVAL:
        update_interval = datetime.timedelta(minutes=app.PROPERS_SEARCH_INTERVAL[check_propers_interval])
    else:
        update_interval = datetime.timedelta(hours=1)
    app.CHECK_PROPERS_INTERVAL = check_propers_interval
    app.proper_finder_scheduler.cycleTime = update_interval


def change_UPDATE_FREQUENCY(freq):
    """
    Change frequency of daily updater thread

    :param freq: New frequency
    """
    app.UPDATE_FREQUENCY = try_int(freq, app.DEFAULT_UPDATE_FREQUENCY)

    if app.UPDATE_FREQUENCY < app.MIN_UPDATE_FREQUENCY:
        app.UPDATE_FREQUENCY = app.MIN_UPDATE_FREQUENCY

    app.version_check_scheduler.cycleTime = datetime.timedelta(hours=app.UPDATE_FREQUENCY)


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

    app.show_update_scheduler.start_time = datetime.time(hour=app.SHOWUPDATE_HOUR)


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
        app.version_check_scheduler.forceRun()


def change_GIT_PATH():
    """
    Recreate the version_check scheduler when GIT_PATH is changed.
    Force a run to clear or set any error messages.
    """
    app.version_check_scheduler = None
    app.version_check_scheduler = scheduler.Scheduler(
        CheckVersion(), cycleTime=datetime.timedelta(hours=app.UPDATE_FREQUENCY), threadName='CHECKVERSION', silent=False)
    app.version_check_scheduler.enable = True
    app.version_check_scheduler.start()
    app.version_check_scheduler.forceRun()


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
        if not app.proper_finder_scheduler.enable:
            log.info(u'Starting PROPERFINDER thread')
            app.proper_finder_scheduler.silent = False
            app.proper_finder_scheduler.enable = True
        else:
            log.info(u'Unable to start PROPERFINDER thread. Already running')
    else:
        app.proper_finder_scheduler.enable = False
        app.trakt_checker_scheduler.silent = True
        log.info(u'Stopping PROPERFINDER thread')


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
        if not app.trakt_checker_scheduler.enable:
            log.info(u'Starting TRAKTCHECKER thread')
            app.trakt_checker_scheduler.silent = False
            app.trakt_checker_scheduler.enable = True
        else:
            log.info(u'Unable to start TRAKTCHECKER thread. Already running')
    else:
        app.trakt_checker_scheduler.enable = False
        app.trakt_checker_scheduler.silent = True
        log.info(u'Stopping TRAKTCHECKER thread')


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
        if not app.subtitles_finder_scheduler.enable:
            log.info(u'Starting SUBTITLESFINDER thread')
            app.subtitles_finder_scheduler.silent = False
            app.subtitles_finder_scheduler.enable = True
        else:
            log.info(u'Unable to start SUBTITLESFINDER thread. Already running')
    else:
        app.subtitles_finder_scheduler.enable = False
        app.subtitles_finder_scheduler.silent = True
        log.info(u'Stopping SUBTITLESFINDER thread')


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
        if not app.post_processor_scheduler.enable:
            log.info(u'Starting POSTPROCESSOR thread')
            app.post_processor_scheduler.silent = False
            app.post_processor_scheduler.enable = True
        else:
            log.info(u'Unable to start POSTPROCESSOR thread. Already running')
    else:
        log.info(u'Stopping POSTPROCESSOR thread')
        app.post_processor_scheduler.enable = False
        app.post_processor_scheduler.silent = True


def change_remove_from_client(new_state):
    """
    Enable/disable TorrentChecker thread
    TODO: Make this return true/false on success/failure

    :param new_state: New desired state
    """
    new_state = checkbox_to_value(new_state)

    if app.REMOVE_FROM_CLIENT == new_state:
        return

    app.REMOVE_FROM_CLIENT = new_state
    if app.REMOVE_FROM_CLIENT:
        if not app.torrent_checker_scheduler.enable:
            log.info(u'Starting TORRENTCHECKER thread')
            app.torrent_checker_scheduler.silent = False
            app.torrent_checker_scheduler.enable = True
        else:
            log.info(u'Unable to start TORRENTCHECKER thread. Already running')
    else:
        app.torrent_checker_scheduler.enable = False
        app.torrent_checker_scheduler.silent = True
        log.info(u'Stopping TORRENTCHECKER thread')


def change_theme(theme_name):
    """
    Hot-swap theme.

    :param theme_name: New theme name
    """
    if theme_name == app.THEME_NAME:
        return False

    old_theme_name = app.THEME_NAME
    old_data_root = os.path.join(app.DATA_ROOT, old_theme_name)

    app.THEME_NAME = theme_name
    app.THEME_DATA_ROOT = os.path.join(app.DATA_ROOT, theme_name)

    static_file_handlers = app.instance.web_server.app.static_file_handlers

    log.info('Switching theme from "{old}" to "{new}"', {'old': old_theme_name, 'new': theme_name})

    for rule in static_file_handlers.target.rules:
        if not rule.target_kwargs['path'] or old_data_root not in rule.target_kwargs['path']:
            # Skip other static file handlers
            continue

        old_path = rule.target_kwargs['path']
        new_path = old_path.replace(old_data_root, app.THEME_DATA_ROOT)
        rule.target_kwargs['path'] = new_path

        log.debug('Changed {old} to {new}', {'old': old_path, 'new': new_path})

    # Reset cache
    StaticFileHandler.reset()

    return True


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

    for cur_host in [host.strip() for host in hosts.split(',') if host.strip()]:
        cleaned_host = clean_host(cur_host, default_port)
        if cleaned_host:
            cleaned_hosts.append(cleaned_host)

    cleaned_hosts = cleaned_hosts or []

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


def convert_csv_string_to_list(value, delimiter=',', trim=False):
    """
    Convert comma or other character delimited strings to a list.

    :param value: The value to convert.f
    :param delimiter: Optionally Change the default delimiter ',' if required.
    :param trim: Optionally trim the individual list items.
    :return: The delimited value as a list.
    """

    if not isinstance(value, (string_types, text_type)):
        return value

    with suppress(AttributeError, ValueError):
        value = value.split(delimiter) if value else []
        if trim:
            value = [_.strip() for _ in value]

    return value


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
        if str(my_val).lower() == 'true':
            my_val = 1
        elif str(my_val).lower() == 'false':
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
        log.debug(u'{item} -> {value}', {u'item': item_name, u'value': my_val})

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
        log.debug(u'{item} -> {value}', {u'item': item_name, u'value': my_val})

    return my_val


################################################################################
# Check_setting_str                                                            #
################################################################################
def check_setting_str(config, cfg_name, item_name, def_val, silent=True, censor_log=False, valid_values=None, encrypted=False):
    # For passwords you must include the word `password` in the item_name or pass `encrypted=True`
    # and add `helpers.encrypt(ITEM_NAME, ENCRYPTION_VERSION)` in save_config()
    if not censor_log:
        censor_level = common.privacy_levels['stupid']
    else:
        censor_level = common.privacy_levels[censor_log]
    privacy_level = common.privacy_levels[app.PRIVACY_LEVEL]
    if bool(item_name.find('password') + 1) or encrypted:
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

    if not silent:
        log.debug(u'{item} -> {value}', {u'item': item_name, u'value': my_val})

    if valid_values and my_val not in valid_values:
        return def_val

    return my_val


################################################################################
# Check_setting_list                                                           #
################################################################################
def check_setting_list(config, cfg_name, item_name, default=None, silent=True, censor_log=False, transform=None,
                       transform_default=0, split_value=False):
    """Check a setting, using the settings section and item name. Expect to return a list."""
    default = default or []

    if not censor_log:
        censor_level = common.privacy_levels['stupid']
    else:
        censor_level = common.privacy_levels[censor_log]
    privacy_level = common.privacy_levels[app.PRIVACY_LEVEL]

    try:
        my_val = config[cfg_name][item_name]
    except Exception:
        my_val = default
        try:
            config[cfg_name][item_name] = my_val
        except Exception:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if privacy_level >= censor_level or (cfg_name, item_name) in iteritems(logger.censored_items):
        if not item_name.endswith('custom_url'):
            logger.censored_items[cfg_name, item_name] = my_val

    if split_value:
        if isinstance(my_val, string_types):
            my_val = split_and_strip(my_val, split_value)

    # Make an attempt to cast the lists values.
    if isinstance(my_val, list) and transform:
        for index, value in enumerate(my_val):
            try:
                my_val[index] = transform(value)
            except ValueError:
                my_val[index] = transform_default

    if not silent:
        log.debug(u'{item} -> {value!r}', {u'item': item_name, u'value': my_val})

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
        'list': check_setting_list,
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
# Save Provider Setting                                                        #
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
        file up to the version required by Medusa
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
            8: 'Convert Plex setting keys',
            9: 'Added setting "enable_manualsearch" for providers (dynamic setting)',
            10: 'Convert all csv config items to lists'
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

            log.info(u'Backing up config before upgrade')
            if not helpers.backup_versioned_file(app.CONFIG_FILE, self.config_version):
                logger.log_error_and_exit(u'Config backup failed, abort upgrading config')
            else:
                log.info(u'Proceeding with upgrade')

            # do the migration, expect a method named _migrate_v<num>
                log.info(u'Migrating config up to version {version} {migration_name}',
                         {'version': next_version, 'migration_name': migration_name})
            getattr(self, '_migrate_v' + str(next_version))()
            self.config_version = next_version

            # save new config after migration
            app.CONFIG_VERSION = self.config_version
            log.info(u'Saving config file to disk')
            app.instance.save_config()

    # Migration v1: Custom naming
    def _migrate_v1(self):
        """
        Reads in the old naming settings from your config and generates a new config template from them.
        """

        app.NAMING_PATTERN = self._name_to_pattern()
        log.info(u"Based on your old settings I'm setting your new naming pattern to: {pattern}",
                 {'pattern': app.NAMING_PATTERN})

        app.NAMING_CUSTOM_ABD = bool(check_setting_int(self.config_obj, 'General', 'naming_dates', 0))

        if app.NAMING_CUSTOM_ABD:
            app.NAMING_ABD_PATTERN = self._name_to_pattern(True)
            log.info(u'Adding a custom air-by-date naming pattern to your config: {pattern}',
                     {'pattern': app.NAMING_ABD_PATTERN})
        else:
            app.NAMING_ABD_PATTERN = naming.name_abd_presets[0]

        app.NAMING_MULTI_EP = int(check_setting_int(self.config_obj, 'General', 'naming_multi_ep_type', 1))

        # see if any of their shows used season folders
        main_db_con = db.DBConnection()
        season_folder_shows = main_db_con.select('SELECT indexer_id FROM tv_shows WHERE flatten_folders = 0 LIMIT 1')

        # if any shows had season folders on then prepend season folder to the pattern
        if season_folder_shows:

            old_season_format = check_setting_str(self.config_obj, 'General', 'season_folders_format', 'Season %02d')

            if old_season_format:
                try:
                    new_season_format = old_season_format % 9
                    new_season_format = str(new_season_format).replace('09', '%0S')
                    new_season_format = new_season_format.replace('9', '%S')

                    log.info(
                        u'Changed season folder format from {old_season_format} to {new_season_format}, '
                        u'prepending it to your naming config',
                        {'old_season_format': old_season_format, 'new_season_format': new_season_format}
                    )
                    app.NAMING_PATTERN = new_season_format + os.sep + app.NAMING_PATTERN

                except (TypeError, ValueError):
                    log.error(u"Can't change {old_season_format} to new season format",
                              {'old_season_format': old_season_format})

        # if no shows had it on then don't flatten any shows and don't put season folders in the config
        else:
            log.info(u"No shows were using season folders before so I'm disabling flattening on all shows")

            # don't flatten any shows at all
            main_db_con.action('UPDATE tv_shows SET flatten_folders = 0')

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
        naming_ep_type = ('%Sx%0E',
                          's%0Se%0E',
                          'S%0SE%0E',
                          '%0Sx%0E')

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

        finalName = ''

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
            finalName = re.sub(r'\s+', '.', finalName)

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
            old_newznab_data_list = old_newznab_data.split('!!!')

            for cur_provider_data in old_newznab_data_list:
                try:
                    name, url, key, enabled = cur_provider_data.split('|')
                except ValueError:
                    log.error(u'Skipping Newznab provider string: {cur_provider_data!r}, incorrect format',
                              {'cur_provider_data': cur_provider_data})
                    continue

                if name == 'Sick Beard Index':
                    key = '0'

                if name == 'NZBs.org':
                    cat_ids = '5030,5040,5060,5070,5090'
                else:
                    cat_ids = '5030,5040,5060'

                cur_provider_data_list = [name, url, key, cat_ids, enabled]
                new_newznab_data.append('|'.join(cur_provider_data_list))

            app.NEWZNAB_DATA = '!!!'.join(new_newznab_data)

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
                log.info(u'Upgrading {metadata_name} metadata, old value: {value}',
                         {'metadata_name': metadata_name, 'value': metadata})
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
                log.info(u'Upgrading {metadata_name} metadata, new value: {value}',
                         {'metadata_name': metadata_name, 'value': metadata})

            elif len(cur_metadata) == 10:

                metadata = '|'.join(cur_metadata)
                log.info(u'Keeping {metadata_name} metadata, value: {value}',
                         {'metadata_name': metadata_name, 'value': metadata})

            else:
                log.error(u'Skipping {metadata_name} metadata {metadata!r}, incorrect format',
                          {'metadata_name': metadata_name, 'metadata': metadata})
                metadata = '0|0|0|0|0|0|0|0|0|0'
                log.info(u'Setting {metadata_name} metadata, new value: {value}',
                         {'metadata_name': metadata_name, 'value': metadata})

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
        app.KODI_USERNAME = check_setting_str(self.config_obj, 'XBMC', 'xbmc_username', '', censor_log='low')
        app.KODI_PASSWORD = check_setting_str(self.config_obj, 'XBMC', 'xbmc_password', '', censor_log='low')
        app.METADATA_KODI = check_setting_str(self.config_obj, 'General', 'metadata_xbmc', '0|0|0|0|0|0|0|0|0|0')
        app.METADATA_KODI_12PLUS = check_setting_str(self.config_obj, 'General', 'metadata_xbmc_12plus', '0|0|0|0|0|0|0|0|0|0')

    # Migration v6: Use version 2 for password encryption
    def _migrate_v7(self):
        app.ENCRYPTION_VERSION = 2

    def _migrate_v8(self):
        app.PLEX_CLIENT_HOST = check_setting_str(self.config_obj, 'Plex', 'plex_host', '')
        app.PLEX_SERVER_USERNAME = check_setting_str(self.config_obj, 'Plex', 'plex_username', '', censor_log='low')
        app.PLEX_SERVER_PASSWORD = check_setting_str(self.config_obj, 'Plex', 'plex_password', '', censor_log='low')
        app.USE_PLEX_SERVER = bool(check_setting_int(self.config_obj, 'Plex', 'use_plex', 0))

    def _migrate_v9(self):
        """
        Migrate to config version 9
        """
        # Added setting 'enable_manualsearch' for providers (dynamic setting)
        pass

    def _migrate_v10(self):
        """
        Convert all csv stored items as 'real' lists. ConfigObj provides a way for storing lists. These are saved
        as comma separated values, using this the format documented here:
        http://configobj.readthedocs.io/en/latest/configobj.html?highlight=lists#list-values
        """

        def get_providers_from_data(providers_string):
            """Split the provider string into providers, and get the provider names."""
            return [provider.split('|')[0].upper() for provider in providers_string.split('!!!') if provider]

        def make_id(name):
            """Make ID of the provider."""
            if not name:
                return ''

            return re.sub(r'[^\w\d_]', '_', str(name).strip().upper())

        def get_rss_torrent_providers_list(data):
            """Get RSS torrent provider list."""
            providers_list = [_ for _ in (make_rss_torrent_provider(_) for _ in data.split('!!!')) if _]
            seen_values = set()
            providers_set = []

            for provider in providers_list:
                value = provider.name

                if value not in seen_values:
                    providers_set.append(provider)
                    seen_values.add(value)

            return [_ for _ in providers_set if _]

        def make_rss_torrent_provider(config):
            """Create new RSS provider."""
            if not config:
                return None

            cookies = ''
            enable_backlog = 0
            enable_daily = 0
            enable_manualsearch = 0
            search_fallback = 0
            search_mode = 'eponly'
            title_tag = 'title'

            try:
                values = config.split('|')

                if len(values) == 9:
                    name, url, cookies, title_tag, enabled, search_mode, search_fallback, enable_daily, enable_backlog = values
                elif len(values) == 10:
                    name, url, cookies, title_tag, enabled, search_mode, search_fallback, enable_daily, enable_backlog, enable_manualsearch = values
                elif len(values) == 8:
                    name, url, cookies, enabled, search_mode, search_fallback, enable_daily, enable_backlog = values
                else:
                    enabled = values[4]
                    name = values[0]
                    url = values[1]
            except ValueError:
                log.error('Skipping RSS Torrent provider string: {config}, incorrect format', {'config': config})
                return None

            new_provider = TorrentRssProvider(
                name, url, cookies=cookies, title_tag=title_tag, search_mode=search_mode,
                search_fallback=search_fallback,
                enable_daily=enable_daily, enable_backlog=enable_backlog, enable_manualsearch=enable_manualsearch
            )
            new_provider.enabled = enabled == '1'

            return new_provider

        # General
        app.GIT_RESET_BRANCHES = convert_csv_string_to_list(self.config_obj['General']['git_reset_branches'])
        app.ALLOWED_EXTENSIONS = convert_csv_string_to_list(self.config_obj['General']['allowed_extensions'])
        app.PROVIDER_ORDER = convert_csv_string_to_list(self.config_obj['General']['provider_order'], ' ')
        app.ROOT_DIRS = convert_csv_string_to_list(self.config_obj['General']['root_dirs'], '|')
        app.SYNC_FILES = convert_csv_string_to_list(self.config_obj['General']['sync_files'])
        app.IGNORE_WORDS = convert_csv_string_to_list(self.config_obj['General']['ignore_words'])
        app.PREFERRED_WORDS = convert_csv_string_to_list(self.config_obj['General']['preferred_words'])
        app.UNDESIRED_WORDS = convert_csv_string_to_list(self.config_obj['General']['undesired_words'])
        app.TRACKERS_LIST = convert_csv_string_to_list(self.config_obj['General']['trackers_list'])
        app.REQUIRE_WORDS = convert_csv_string_to_list(self.config_obj['General']['require_words'])
        app.IGNORED_SUBS_LIST = convert_csv_string_to_list(self.config_obj['General']['ignored_subs_list'])
        app.BROKEN_PROVIDERS = convert_csv_string_to_list(self.config_obj['General']['broken_providers'])
        app.EXTRA_SCRIPTS = convert_csv_string_to_list(self.config_obj['General']['extra_scripts'], '|')

        # Metadata
        app.METADATA_KODI = convert_csv_string_to_list(self.config_obj['General']['metadata_kodi'], '|')
        app.METADATA_KODI_12PLUS = convert_csv_string_to_list(self.config_obj['General']['metadata_kodi_12plus'], '|')
        app.METADATA_MEDIABROWSER = convert_csv_string_to_list(self.config_obj['General']['metadata_mediabrowser'], '|')
        app.METADATA_PS3 = convert_csv_string_to_list(self.config_obj['General']['metadata_ps3'], '|')
        app.METADATA_WDTV = convert_csv_string_to_list(self.config_obj['General']['metadata_wdtv'], '|')
        app.METADATA_TIVO = convert_csv_string_to_list(self.config_obj['General']['metadata_tivo'], '|')
        app.METADATA_MEDE8ER = convert_csv_string_to_list(self.config_obj['General']['metadata_mede8er'], '|')

        # Subtitles
        app.SUBTITLES_LANGUAGES = convert_csv_string_to_list(self.config_obj['Subtitles']['subtitles_languages'])
        app.SUBTITLES_SERVICES_LIST = convert_csv_string_to_list(self.config_obj['Subtitles']['SUBTITLES_SERVICES_LIST'])
        app.SUBTITLES_SERVICES_ENABLED = convert_csv_string_to_list(self.config_obj['Subtitles']['SUBTITLES_SERVICES_ENABLED'], '|')
        app.SUBTITLES_EXTRA_SCRIPTS = convert_csv_string_to_list(self.config_obj['Subtitles']['subtitles_extra_scripts'], '|')
        app.SUBTITLES_PRE_SCRIPTS = convert_csv_string_to_list(self.config_obj['Subtitles']['subtitles_pre_scripts'], '|')

        # Notifications
        app.KODI_HOST = convert_csv_string_to_list(self.config_obj['KODI']['kodi_host'])
        app.PLEX_SERVER_HOST = convert_csv_string_to_list(self.config_obj['Plex']['plex_server_host'])
        app.PLEX_CLIENT_HOST = convert_csv_string_to_list(self.config_obj['Plex']['plex_client_host'])
        app.PROWL_API = convert_csv_string_to_list(self.config_obj['Prowl']['prowl_api'])
        app.PUSHOVER_DEVICE = convert_csv_string_to_list(self.config_obj['Pushover']['pushover_device'])
        app.EMAIL_LIST = convert_csv_string_to_list(self.config_obj['Email']['email_list'])

        try:
            # migrate rsstorrent providers
            from medusa.providers.torrent.rss.rsstorrent import TorrentRssProvider

            # Create the new list of torrent rss providers, with only the id stored.
            app.TORRENTRSS_PROVIDERS = get_providers_from_data(self.config_obj['TorrentRss']['torrentrss_data'])

            # Create the torrent providers from the old rsstorrent piped separated data.
            app.torrentRssProviderList = get_rss_torrent_providers_list(self.config_obj['TorrentRss']['torrentrss_data'])
        except KeyError:
            app.TORRENTRSS_PROVIDERS = []

        try:
            # migrate newznab providers.
            # Newznabprovider needs to be imported lazy, as the module will also import other providers to early.
            from medusa.providers.nzb.newznab import NewznabProvider

            # Create the newznab providers from the old newznab piped separated data.
            app.newznabProviderList = NewznabProvider.get_providers_list(
                self.config_obj['Newznab']['newznab_data']
            )

            app.NEWZNAB_PROVIDERS = [make_id(provider.name) for provider in app.newznabProviderList if not provider.default]
        except KeyError:
            app.NEWZNAB_PROVIDERS = []
