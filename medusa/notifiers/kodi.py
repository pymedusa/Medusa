# coding=utf-8

import base64
import json
import logging
import socket
import time

from medusa import app, common
from medusa.helper.encoding import ss
from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import quote, unquote, unquote_plus, urlencode
from six import text_type
from six.moves.http_client import BadStatusLine
from six.moves.urllib.error import URLError
from six.moves.urllib.request import Request, urlopen

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def _get_kodi_version(self, host, username, password, dest_app='KODI'):
        """Returns KODI JSON-RPC API version (odd # = dev, even # = stable)

        Sends a request to the KODI host using the JSON-RPC to determine if
        the legacy API or if the JSON-RPC API functions should be used.

        Fallback to testing legacy HTTPAPI before assuming it is just a badly configured host.

        Args:
            host: KODI webserver host:port
            username: KODI webserver username
            password: KODI webserver password

        Returns:
            Returns API number or False

            List of possible known values:
                API | KODI Version
               -----+---------------
                 2  | v10 (Dharma)
                 3  | (pre Eden)
                 4  | v11 (Eden)
                 5  | (pre Frodo)
                 6  | v12 (Frodo) / v13 (Gotham)

        """

        # since we need to maintain python 2.5 compatibility we can not pass a timeout delay to urllib2 directly (python 2.6+)
        # override socket timeout to reduce delay for this call alone
        socket.setdefaulttimeout(10)

        checkCommand = json.dumps({
            'jsonrpc': '2.0',
            'method': 'JSONRPC.Version',
            'id': 1,
        })
        result = self._send_to_kodi_json(checkCommand, host, username, password, dest_app)

        # revert back to default socket timeout
        socket.setdefaulttimeout(app.SOCKET_TIMEOUT)

        if result:
            return result['result']['version']
        else:
            # fallback to legacy HTTPAPI method
            testCommand = {'command': 'Help'}
            request = self._send_to_kodi(testCommand, host, username, password, dest_app)
            if request:
                # return a fake version number, so it uses the legacy method
                return 1
            else:
                return False

    def _notify_kodi(self, message, title='Medusa', host=None, username=None, password=None, force=False, dest_app='KODI'):  # pylint: disable=too-many-arguments
        """Internal wrapper for the notify_snatch and notify_download functions

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

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not app.USE_KODI and not force:
            log.debug(u'Notification for {app} not enabled, skipping this notification',
                      {'app': dest_app})
            return False

        result = ''
        for curHost in [x.strip() for x in host.split(',') if x.strip()]:
            log.debug(u'Sending {app} notification to {host} - {msg}',
                      {'app': dest_app, 'host': curHost, 'msg': message})

            kodiapi = self._get_kodi_version(curHost, username, password, dest_app)
            if kodiapi:
                if kodiapi <= 4:
                    log.debug(u'Detected {app} version <= 11, using {app} HTTP API',
                              {'app': dest_app})
                    command = {
                        'command': 'ExecBuiltIn',
                        'parameter': 'Notification({title},{msg})'.format(
                            title=title.encode('utf-8'),
                            msg=message.encode('utf-8'),
                        )
                    }
                    notifyResult = self._send_to_kodi(command, curHost, username, password)
                    if notifyResult:
                        result += curHost + ':' + str(notifyResult)
                else:
                    log.debug(u'Detected {app} version >= 12, using {app} JSON API',
                              {'app': dest_app})
                    command = json.dumps({
                        'jsonrpc': '2.0',
                        'method': 'GUI.ShowNotification',
                        'params': {
                            'title': title.encode('utf-8'),
                            'message': message.encode('utf-8'),
                            'image': app.LOGO_URL,
                        },
                        'id': '1',
                    })
                    notifyResult = self._send_to_kodi_json(command, curHost, username, password, dest_app)
                    if notifyResult and notifyResult.get('result'):  # pylint: disable=no-member
                        result += curHost + ':' + notifyResult['result'].decode(app.SYS_ENCODING)
            else:
                if app.KODI_ALWAYS_ON or force:
                    log.warning(
                        u'Failed to detect {app} version for {host},'
                        u' check configuration and try again.',
                        {'app': dest_app, 'host': curHost}
                    )
                result += curHost + ':False'

        return result

    def _send_update_library(self, host, showName=None):
        """Internal wrapper for the update library function to branch the logic for JSON-RPC or legacy HTTP API

        Checks the KODI API version to branch the logic to call either the legacy HTTP API or the newer JSON-RPC over HTTP methods.

        Args:
            host: KODI webserver host:port
            showName: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False, if the update was successful

        """

        log.debug(u'Sending request to update library for KODI host: {0}', host)

        kodiapi = self._get_kodi_version(host, app.KODI_USERNAME, app.KODI_PASSWORD)
        if kodiapi:
            update = self._update_library if kodiapi <= 4 else self._update_library_json
            # try to update for just the show, if it fails, do full update if enabled
            if not update(host, showName) and app.KODI_UPDATE_FULL:
                log.debug(u'Single show update failed, falling back to full update')
                return update(host)
            else:
                return True
        elif app.KODI_ALWAYS_ON:
            log.warning(u'Failed to detect KODI version for {host},'
                        u' check configuration and try again.',
                        {'host': host})

        return False

    # #############################################################################
    # Legacy HTTP API (pre KODI 12) methods
    ##############################################################################

    @staticmethod
    def _send_to_kodi(command, host=None, username=None, password=None, dest_app='KODI'):  # pylint: disable=too-many-arguments
        """Handles communication to KODI servers via HTTP API

        Args:
            command: Dictionary of field/data pairs, encoded via urllib and passed to the KODI API via HTTP
            host: KODI webserver host:port
            username: KODI webserver username
            password: KODI webserver password

        Returns:
            Returns response.result for successful commands or False if there was an error

        """

        # fill in omitted parameters
        username = username or app.KODI_USERNAME
        password = password or app.KODI_PASSWORD

        if not host:
            log.warning(u'No {app} host passed, aborting update',
                        {'app': dest_app})
            return False

        for key in command:
            if isinstance(command[key], text_type):
                command[key] = command[key].encode('utf-8')

        enc_command = urlencode(command)
        log.debug(u'{app} encoded API command: {cmd!r}',
                  {'app': dest_app, 'cmd': enc_command})

        # url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, enc_command)  # maybe need for old plex?
        url = 'http://%s/kodiCmds/kodiHttp/?%s' % (host, enc_command)
        try:
            req = Request(url)
            # if we have a password, use authentication
            if password:
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader = 'Basic %s' % base64string
                req.add_header('Authorization', authheader)
                log.debug(u'Contacting {0} (with auth header) via url: {1}', dest_app, ss(url))
            else:
                log.debug(u'Contacting {0} via url: {1}', dest_app, ss(url))

            try:
                response = urlopen(req)
            except (BadStatusLine, URLError) as e:
                log.debug(u'Unable to contact {0} HTTP at {1!r} : {2!r}', dest_app, url, ex(e))
                return False

            result = response.read().decode(app.SYS_ENCODING)
            response.close()

            log.debug(u'{0} HTTP response: {1}', dest_app, result.replace('\n', ''))
            return result

        except Exception as e:
            log.debug(u'Unable to contact {0} HTTP at {1!r} : {2!r}', dest_app, url, ex(e))
            return False

    def _update_library(self, host=None, showName=None):  # pylint: disable=too-many-locals, too-many-return-statements
        """Handles updating KODI host via HTTP API

        Attempts to update the KODI video library for a specific tv show if passed,
        otherwise update the whole library if enabled.

        Args:
            host: KODI webserver host:port
            showName: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """

        if not host:
            log.warning(u'No KODI host passed, aborting update')
            return False

        log.debug(u'Updating KODI library via HTTP method for host: {0}', host)

        # if we're doing per-show
        if showName:
            log.debug(u'Updating library in KODI via HTTP method for show {0}', showName)

            pathSql = (
                "SELECT path.strPath "
                "FROM path, tvshow, tvshowlinkpath "
                "WHERE tvshow.c00 = '%s'"
                " AND tvshowlinkpath.idShow = tvshow.idShow"
                " AND tvshowlinkpath.idPath = path.idPath" % showName
            )

            # use this to get xml back for the path lookups
            xmlCommand = {
                'command': 'SetResponseFormat(webheader;false;webfooter;false;header;<xml>;footer;</xml>;opentag;<tag>;closetag;</tag>;closefinaltag;false)'
            }
            # sql used to grab path(s)
            sqlCommand = {'command': 'QueryVideoDatabase(%s)' % pathSql}
            # set output back to default
            resetCommand = {'command': 'SetResponseFormat()'}

            # set xml response format, if this fails then don't bother with the rest
            request = self._send_to_kodi(xmlCommand, host)
            if not request:
                return False

            sqlXML = self._send_to_kodi(sqlCommand, host)
            request = self._send_to_kodi(resetCommand, host)

            if not sqlXML:
                log.debug(u'Invalid response for {0} on {1}', showName, host)
                return False

            encSqlXML = quote(sqlXML, ':\\/<>')
            try:
                et = etree.fromstring(encSqlXML)
            except SyntaxError as e:
                log.error(u'Unable to parse XML returned from KODI: {0}', ex(e))
                return False

            paths = et.findall('.//field')

            if not paths:
                log.debug(u'No valid paths found for {0} on {1}', showName, host)
                return False

            for path in paths:
                # we do not need it double-encoded, gawd this is dumb
                unEncPath = unquote(path.text).decode(app.SYS_ENCODING)
                log.debug(u'KODI Updating {0} on {1} at {2}', showName, host, unEncPath)
                updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'KODI.updatelibrary(video, %s)' % unEncPath}
                request = self._send_to_kodi(updateCommand, host)
                if not request:
                    log.warning(u'Update of show directory failed on {0} on {1} at {2}', showName, host, unEncPath)
                    return False
                # sleep for a few seconds just to be sure kodi has a chance to finish each directory
                if len(paths) > 1:
                    time.sleep(5)
        # do a full update if requested
        else:
            log.debug(u'Doing Full Library KODI update on host: {0}', host)
            updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'KODI.updatelibrary(video)'}
            request = self._send_to_kodi(updateCommand, host)

            if not request:
                log.warning(u'KODI Full Library update failed on: {0}', host)
                return False

        return True

    ##############################################################################
    # JSON-RPC API (KODI 12+) methods
    ##############################################################################

    @staticmethod
    def _send_to_kodi_json(command, host=None, username=None, password=None, dest_app='KODI'):
        """Handles communication to KODI servers via JSONRPC

        Args:
            command: Dictionary of field/data pairs, encoded via urllib and passed to the KODI JSON-RPC via HTTP
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

        command = command.encode('utf-8')
        log.debug(u'{0} JSON command: {1}', dest_app, command)

        url = 'http://%s/jsonrpc' % host
        try:
            req = Request(url, command)
            req.add_header('Content-type', 'application/json')
            # if we have a password, use authentication
            if password:
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader = 'Basic %s' % base64string
                req.add_header('Authorization', authheader)
                log.debug(u'Contacting {0} (with auth header) via url: {1}', dest_app, ss(url))
            else:
                log.debug(u'Contacting {0} via url: {1}', dest_app, ss(url))

            try:
                response = urlopen(req)
            except (BadStatusLine, URLError) as e:
                if app.KODI_ALWAYS_ON:
                    log.warning(u'Error while trying to retrieve {0} API version for {1}: {2!r}', dest_app, host, ex(e))
                return False

            # parse the json result
            try:
                result = json.load(response)
                response.close()
                log.debug(u'{0} JSON response: {1}', dest_app, result)
                return result  # need to return response for parsing
            except ValueError as e:
                log.warning(u'Unable to decode JSON: {}', response.read())
                return False

        except IOError as e:
            if app.KODI_ALWAYS_ON:
                log.warning(u'Warning: Unable to contact {0} JSON API at {1}: {2!r}', dest_app, ss(url), ex(e))
            return False

    def clean_library(self):
        """Handles clean library KODI host via HTTP JSON-RPC."""
        if not app.USE_KODI:
            return True
        clean_library = True
        for host in [x.strip() for x in app.KODI_HOST.split(',')]:
            log.info(u'Cleaning KODI library via JSON method for host: {0}', host)
            update_command = json.dumps({
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.Clean',
                'params': {
                    'showdialogs': False,
                },
                'id': 1,
            })
            request = self._send_to_kodi_json(update_command, host)
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

    def _update_library_json(self, host=None, showName=None):  # pylint: disable=too-many-return-statements, too-many-branches
        """Handles updating KODI host via HTTP JSON-RPC

        Attempts to update the KODI video library for a specific tv show if passed,
        otherwise update the whole library if enabled.

        Args:
            host: KODI webserver host:port
            showName: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """

        if not host:
            log.warning(u'No KODI host passed, aborting update')
            return False

        log.info(u'Updating KODI library via JSON method for host: {0}', host)

        # if we're doing per-show
        if showName:
            showName = unquote_plus(showName)
            tvshowid = -1
            path = ''

            log.debug(u'Updating library in KODI via JSON method for show {0}', showName)

            # let's try letting kodi filter the shows
            showsCommand = json.dumps({
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.GetTVShows',
                'params': {
                    'filter': {
                        'field': 'title',
                        'operator': 'is',
                        'value': showName,
                    },
                    'properties': ['title'],
                },
                'id': 'Medusa',
            })

            # get tvshowid by showName
            showsResponse = self._send_to_kodi_json(showsCommand, host)

            if showsResponse and 'result' in showsResponse and 'tvshows' in showsResponse['result']:
                shows = showsResponse['result']['tvshows']
            else:
                # fall back to retrieving the entire show list
                showsCommand = json.dumps({
                    'jsonrpc': '2.0',
                    'method': 'VideoLibrary.GetTVShows',
                    'id': 1,
                })
                showsResponse = self._send_to_kodi_json(showsCommand, host)

                if showsResponse and 'result' in showsResponse and 'tvshows' in showsResponse['result']:
                    shows = showsResponse['result']['tvshows']
                else:
                    log.debug(u'KODI: No tvshows in KODI TV show list')
                    return False

            for show in shows:
                if ('label' in show and show['label'] == showName) or ('title' in show and show['title'] == showName):
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
                pathCommand = json.dumps({
                    'jsonrpc': '2.0',
                    'method': 'VideoLibrary.GetTVShowDetails',
                    'params': {
                        'tvshowid': tvshowid,
                        'properties': ['file'],
                    },
                    'id': 1,
                })
                pathResponse = self._send_to_kodi_json(pathCommand, host)

                path = pathResponse['result']['tvshowdetails']['file']

            log.debug(u'Received Show: {0} with ID: {1} Path: {2}', showName, tvshowid, path)

            if not path:
                log.warning(u'No valid path found for {0} with ID: {1} on {2}', showName, tvshowid, host)
                return False

            log.debug(u'KODI Updating {} on {} at {}', showName, host, path)
            updateCommand = json.dumps({
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.Scan',
                'params': {
                    'directory': path,
                },
                'id': 1,
            })
            request = self._send_to_kodi_json(updateCommand, host)
            if not request:
                log.warning(u'Update of show directory failed on {0} on {1} at {2}', showName, host, path)
                return False

            # catch if there was an error in the returned request
            for r in request:
                if 'error' in r:
                    log.warning(u'Error while attempting to update show directory for {0} on {1} at {2} ', showName, host, path)
                    return False

        # do a full update if requested
        else:
            log.debug(u'Doing Full Library KODI update on host: {0}', host)
            updateCommand = json.dumps({
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.Scan',
                'id': 1,
            })
            request = self._send_to_kodi_json(updateCommand, host)

            if not request:
                log.warning(u'KODI Full Library update failed on: {0}', host)
                return False

        return True

    ##############################################################################
    # Public functions which will call the JSON or Legacy HTTP API methods
    ##############################################################################

    def notify_snatch(self, ep_name, is_proper):
        if app.KODI_NOTIFY_ONSNATCH:
            self._notify_kodi(ep_name, common.notifyStrings[(common.NOTIFY_SNATCH, common.NOTIFY_SNATCH_PROPER)[is_proper]])

    def notify_download(self, ep_name):
        if app.KODI_NOTIFY_ONDOWNLOAD:
            self._notify_kodi(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def notify_subtitle_download(self, ep_name, lang):
        if app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notify_kodi(ep_name + ': ' + lang, common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD])

    def notify_git_update(self, new_version='??'):
        if app.USE_KODI:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._notify_kodi(update_text + new_version, title)

    def notify_login(self, ipaddress=''):
        if app.USE_KODI:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._notify_kodi(update_text.format(ipaddress), title)

    def test_notify(self, host, username, password):
        return self._notify_kodi('Testing KODI notifications from Medusa', 'Test Notification', host, username, password, force=True)

    def update_library(self, showName=None):
        """Public wrapper for the update library functions to branch the logic for JSON-RPC or legacy HTTP API

        Checks the KODI API version to branch the logic to call either the legacy HTTP API or the newer JSON-RPC over HTTP methods.
        Do the ability of accepting a list of hosts delimited by comma, only one host is updated, the first to respond with success.
        This is a workaround for SQL backend users as updating multiple clients causes duplicate entries.
        Future plan is to revist how we store the host/ip/username/pw/options so that it may be more flexible.

        Args:
            showName: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """

        if app.USE_KODI and app.KODI_UPDATE_LIBRARY:
            if not app.KODI_HOST:
                log.debug(u'No KODI hosts specified, check your settings')
                return False

            # either update each host, or only attempt to update until one successful result
            result = 0
            for host in [x.strip() for x in app.KODI_HOST.split(',')]:
                if self._send_update_library(host, showName):
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
