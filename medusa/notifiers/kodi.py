# coding=utf-8

"""Kodi notifier module."""
from __future__ import unicode_literals

import logging
from builtins import object

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

from requests.auth import HTTPBasicAuth
from requests.compat import unquote_plus
from requests.exceptions import HTTPError, RequestException

from six import string_types, text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


session = MedusaSession()


class Notifier(object):
    """Kodi notifier class."""

    def _get_kodi_version(self, host, username, password, dest_app='KODI'):
        """Return KODI JSON-RPC API version (odd # = dev, even # = stable).

        Sends a request to the KODI host using the JSON-RPC to determine if
        the legacy API or if the JSON-RPC API functions should be used.

        Warn the user if it's trying to connect to a legacy Kodi (< v.12).

        Args:
            host: KODI webserver host:port
            username: KODI webserver username
            password: KODI webserver password

        Returns:
            Returns API number or False

            List of possible known values:
                API | KODI Version
               -----+---------------
                 2  | v10 (Dharma) (not supported)
                 3  | (pre Eden) (not supported)
                 4  | v11 (Eden) (not supported)
                 5  | (pre Frodo) (not supported)
                 6  | v12 (Frodo) / v13 (Gotham) / v14 (Helix) / v15 (Isengard) / 16 (Jarvis)
                 8  | v18 (Krypton)

        """
        check_command = {
            'jsonrpc': '2.0',
            'method': 'JSONRPC.Version',
            'id': 1,
        }
        result = self._send_to_kodi(check_command, host, username, password, dest_app)

        if result and 'error' not in result:
            if isinstance(result['result']['version'], dict):
                return result['result']['version'].get('major')
            return result['result']['version']
        else:
            return False

    def _notify_kodi(self, title, message, host=None, username=None, password=None,
                     force=False, dest_app='KODI'):
        """Private wrapper for the notify_snatch and notify_download functions.

        Detects JSON-RPC version then branches the logic for either the JSON-RPC or legacy HTTP API methods.

        Args:
            message: Message body of the notice to send
            title: Title of the notice to send
            host: KODI webserver host:port
            username: KODI webserver username
            password: KODI webserver password
            force: Used for the Test method to override config saftey checks

        Returns:
            Returns a list results in the format of host:ip:result
            The result will either be 'OK' or False, this is used to be parsed by the calling function.

        """
        # fill in omitted parameters
        if not host:
            host = app.KODI_HOST
        if not username:
            username = app.KODI_USERNAME
        if not password:
            password = app.KODI_PASSWORD

        # Sanitize host when not passed as a list
        if isinstance(host, (string_types, text_type)):
            host = host.split(',')

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not app.USE_KODI and not force:
            log.debug(u'Notification for {app} not enabled, skipping this notification',
                      {'app': dest_app})
            return False

        result = ''
        for cur_host in [x.strip() for x in host if x.strip()]:
            log.debug(u'Sending {app} notification to {host} - {msg}',
                      {'app': dest_app, 'host': cur_host, 'msg': message})

            kodi_api = self._get_kodi_version(cur_host, username, password, dest_app)
            if kodi_api:
                if kodi_api <= 4:
                    log.warning(u'Detected {app} version <= 11, this version is not supported by Medusa. '
                                u'Please upgrade to the Kodi 12 or above.',
                                {'app': dest_app})
                else:
                    log.debug(u'Detected {app} version >= 12, using {app} JSON API',
                              {'app': dest_app})
                    command = {
                        'jsonrpc': '2.0',
                        'method': 'GUI.ShowNotification',
                        'params': {
                            'title': title,
                            'message': message,
                            'image': app.LOGO_URL,
                        },
                        'id': '1',
                    }
                    notify_result = self._send_to_kodi(command, cur_host, username, password, dest_app)
                    if notify_result and notify_result.get('result'):
                        result += '{cur_host}:{notify_result}'.format(cur_host=cur_host, notify_result=notify_result['result'])
            else:
                if app.KODI_ALWAYS_ON or force:
                    log.warning(
                        u'Failed to detect {app} version for {host},'
                        u' check configuration and try again.',
                        {'app': dest_app, 'host': cur_host}
                    )
                result += cur_host + ':False'

        return result

    def _send_update_library(self, host, series_name=None):
        """Private wrapper for the update library function.

        Args:
            host: KODI webserver host:port
            series_name: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False, if the update was successful

        """
        log.debug(u'Sending request to update library for KODI host: {0}', host)

        kodi_api = self._get_kodi_version(host, app.KODI_USERNAME, app.KODI_PASSWORD)
        if kodi_api:
            update = self._update_library
            # try to update for just the show, if it fails, do full update if enabled
            if not update(host, series_name) and app.KODI_UPDATE_FULL:
                log.debug(u'Single show update failed, falling back to full update')
                return update(host)
            else:
                return True
        elif app.KODI_ALWAYS_ON:
            log.warning(u'Failed to detect KODI version for {host},'
                        u' check configuration and try again.',
                        {'host': host})

        return False

    ##############################################################################
    # JSON-RPC API (KODI 12+) methods
    ##############################################################################

    @staticmethod
    def _send_to_kodi(command, host=None, username=None, password=None, dest_app='KODI'):
        """Handle communication to KODI servers via JSONRPC.

        Args:
            command: Dictionary of field/data pairs, passed to the KODI JSON-RPC via HTTP
            host: KODI webserver host:port
            username: KODI webserver username
            password: KODI webserver password

        Returns:
            Returns response.result for successful commands or False if there was an error

        """
        # fill in omitted parameters
        if not username:
            username = app.KODI_USERNAME
        if not password:
            password = app.KODI_PASSWORD

        if not host:
            log.warning(u'No {0} host passed, aborting update', dest_app)
            return False

        log.debug(u'{0} JSON command: {1}', dest_app, command)

        url = 'http://%s/jsonrpc' % host
        try:

            # if we have a password, use authentication
            if password:
                basic_auth = HTTPBasicAuth(username, password)
                log.debug(u'Contacting {0} (with auth header) via url: {1}', dest_app, url)
            else:
                basic_auth = None
                log.debug(u'Contacting {0} via url: {1}', dest_app, url)

            headers = {'Content-Type': 'application/json'}

            try:
                response = session.post(url, headers=headers, json=command, auth=basic_auth, timeout=app.SOCKET_TIMEOUT)
                response.raise_for_status()
            except HTTPError as error:
                if app.KODI_ALWAYS_ON:
                    log.warning(u'Http error while trying to retrieve {0} API version for {1}: {2!r}',
                                dest_app, host, error)
                return False
            except RequestException as error:
                if app.KODI_ALWAYS_ON:
                    log.warning(u'Connection error while trying to retrieve {0} API version for {1}: {2!r}',
                                dest_app, host, error)
                return False
            except Exception as error:
                log.exception(u'An error occurred while trying to retrieve {0} API version for {1}: {2!r}',
                              dest_app, host, error)
                return False

            # parse the json result
            try:
                result = response.json()
                log.debug(u'{0} JSON response: {1}', dest_app, result)
                return result  # need to return response for parsing
            except ValueError:
                log.warning(u'Unable to decode JSON: {0}', response.text)
                return False

        except IOError as error:
            if app.KODI_ALWAYS_ON:
                log.warning(u'Warning: Unable to contact {0} JSON API at {1}: {2!r}', dest_app, url, error)
            return False

    def clean_library(self):
        """Handle clean library KODI host via HTTP JSON-RPC."""
        if not app.USE_KODI:
            return True
        clean_library = True
        for host in [x.strip() for x in app.KODI_HOST]:
            log.info(u'Cleaning KODI library via JSON method for host: {0}', host)
            update_command = {
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.Clean',
                'params': {
                    'showdialogs': False,
                },
                'id': 1,
            }
            request = self._send_to_kodi(update_command, host)
            if not request:
                if app.KODI_ALWAYS_ON:
                    log.warning(u'KODI library clean failed for host: {0}', host)
                clean_library = False
                if app.KODI_UPDATE_ONLYFIRST:
                    break
                else:
                    continue

            # catch if there was an error in the returned request
            for r in request:
                if 'error' in r:
                    if app.KODI_ALWAYS_ON:
                        log.warning(u'Error while attempting to clean library for host: {0}', host)
                    clean_library = False
            if app.KODI_UPDATE_ONLYFIRST:
                break

        # If no errors, return True. Otherwise keep sending command until all hosts are cleaned
        return clean_library

    def _update_library(self, host=None, series_name=None):
        """Handle updating KODI host via HTTP JSON-RPC.

        Attempts to update the KODI video library for a specific tv show if passed,
        otherwise update the whole library if enabled.

        Args:
            host: KODI webserver host:port
            series_name: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """
        if not host:
            log.warning(u'No KODI host passed, aborting update')
            return False

        log.info(u'Updating KODI library via JSON method for host: {0}', host)

        # if we're doing per-show
        if series_name:
            series_name = unquote_plus(series_name)
            tvshowid = -1
            path = ''

            log.debug(u'Updating library in KODI via JSON method for show {0}', series_name)

            # let's try letting kodi filter the shows
            shows_command = {
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.GetTVShows',
                'params': {
                    'filter': {
                        'field': 'title',
                        'operator': 'is',
                        'value': series_name,
                    },
                    'properties': ['title'],
                },
                'id': 'Medusa',
            }

            # get tvshowid by series_name
            series_response = self._send_to_kodi(shows_command, host)

            if series_response and 'result' in series_response and 'tvshows' in series_response['result']:
                shows = series_response['result']['tvshows']
            else:
                # fall back to retrieving the entire show list
                shows_command = {
                    'jsonrpc': '2.0',
                    'method': 'VideoLibrary.GetTVShows',
                    'id': 1,
                }
                series_response = self._send_to_kodi(shows_command, host)

                if series_response and 'result' in series_response and 'tvshows' in series_response['result']:
                    shows = series_response['result']['tvshows']
                else:
                    log.debug(u'KODI: No tvshows in KODI TV show list')
                    return False

            for show in shows:
                if ('label' in show and show['label'] == series_name) or ('title' in show and show['title'] == series_name):
                    tvshowid = show['tvshowid']
                    # set the path is we have it already
                    if 'file' in show:
                        path = show['file']

                    break

            # this can be big, so free some memory
            del shows

            # we didn't find the show (exact match), thus revert to just doing a full update if enabled
            if tvshowid == -1:
                log.debug(u'Exact show name not matched in KODI TV show list')
                return False

            # lookup tv-show path if we don't already know it
            if not path:
                path_command = {
                    'jsonrpc': '2.0',
                    'method': 'VideoLibrary.GetTVShowDetails',
                    'params': {
                        'tvshowid': tvshowid,
                        'properties': ['file'],
                    },
                    'id': 1,
                }
                path_response = self._send_to_kodi(path_command, host)

                path = path_response['result']['tvshowdetails']['file']

            log.debug(u'Received Show: {0} with ID: {1} Path: {2}', series_name, tvshowid, path)

            if not path:
                log.warning(u'No valid path found for {0} with ID: {1} on {2}', series_name, tvshowid, host)
                return False

            log.debug(u'KODI Updating {0} on {1} at {2}', series_name, host, path)
            update_command = {
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.Scan',
                'params': {
                    'directory': path,
                },
                'id': 1,
            }
            request = self._send_to_kodi(update_command, host)
            if not request:
                log.warning(u'Update of show directory failed on {0} on {1} at {2}', series_name, host, path)
                return False

            # catch if there was an error in the returned request
            for r in request:
                if 'error' in r:
                    log.warning(u'Error while attempting to update show directory for {0} on {1} at {2} ',
                                series_name, host, path)
                    return False

        # do a full update if requested
        else:
            log.debug(u'Doing Full Library KODI update on host: {0}', host)
            update_command = {
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.Scan',
                'id': 1,
            }
            request = self._send_to_kodi(update_command, host)

            if not request:
                log.warning(u'KODI Full Library update failed on: {0}', host)
                return False

        return True

    ##############################################################################
    # Public functions which will call the JSON or Legacy HTTP API methods
    ##############################################################################

    def notify_snatch(self, title, message):
        """Send the snatch message."""
        if app.KODI_NOTIFY_ONSNATCH:
            self._notify_kodi(title, message)

    def notify_download(self, ep_obj):
        """Send the download message."""
        if app.KODI_NOTIFY_ONDOWNLOAD:
            self._notify_kodi(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_obj.pretty_name_with_quality())

    def notify_subtitle_download(self, ep_obj, lang):
        """Send the subtitle download message."""
        if app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notify_kodi(common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD], ep_obj.pretty_name() + ': ' + lang)

    def notify_git_update(self, new_version='??'):
        """Send update available message."""
        if app.USE_KODI:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._notify_kodi(title, update_text + new_version)

    def notify_login(self, ipaddress=''):
        """Send the new login message."""
        if app.USE_KODI:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._notify_kodi(title, update_text.format(ipaddress))

    def test_notify(self, host, username, password):
        """Test notifier."""
        return self._notify_kodi('Test Notification', 'Testing KODI notifications from Medusa', host, username,
                                 password, force=True)

    def update_library(self, series_name=None):
        """Public wrapper for the update library functions to branch the logic for JSON-RPC or legacy HTTP API.

        Checks the KODI API version to branch the logic to call either the legacy HTTP API or the newer JSON-RPC over HTTP methods.
        Do the ability of accepting a list of hosts delimited by comma, only one host is updated, the first to respond with success.
        This is a workaround for SQL backend users as updating multiple clients causes duplicate entries.
        Future plan is to revist how we store the host/ip/username/pw/options so that it may be more flexible.

        Args:
            series_name: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """
        if app.USE_KODI and app.KODI_UPDATE_LIBRARY:
            if not app.KODI_HOST:
                log.debug(u'No KODI hosts specified, check your settings')
                return False

            # either update each host, or only attempt to update until one successful result
            result = 0
            for host in [x.strip() for x in app.KODI_HOST]:
                if self._send_update_library(host, series_name):
                    if app.KODI_UPDATE_ONLYFIRST:
                        log.debug(u'Successfully updated {0}, stopped sending update library commands.', host)
                        return True
                else:
                    if app.KODI_ALWAYS_ON:
                        log.warning(u'Failed to detect KODI version for {0}, check configuration and try again.', host)
                    result += 1

            # needed for the 'update kodi' submenu command
            # as it only cares of the final result vs the individual ones
            return not bool(result)
