# coding=utf-8

from __future__ import unicode_literals

import logging
import re
import telnetlib
from builtins import object

from medusa import app
from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urlencode

from six.moves.urllib.request import Request, urlopen

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def notify_settings(self, host):
        """
        Retrieve the settings from a NMJ/Popcorn hour

        host: The hostname/IP of the Popcorn Hour server

        return: True if the settings were retrieved successfully, False otherwise
        """
        # establish a terminal session to the PC
        try:
            terminal = telnetlib.Telnet(host)
        except Exception:
            log.warning(u'Warning: unable to get a telnet session to {0}', host)
            return False

        # tell the terminal to output the necessary info to the screen so we can search it later
        log.debug(u'Connected to {0} via telnet', host)
        terminal.read_until('sh-3.00# ')
        terminal.write('cat /tmp/source\n')
        terminal.write('cat /tmp/netshare\n')
        terminal.write('exit\n')
        tnoutput = terminal.read_all()

        match = re.search(r'(.+\.db)\r\n?(.+)(?=sh-3.00# cat /tmp/netshare)', tnoutput)

        # if we found the database in the terminal output then save that database to the config
        if match:
            database = match.group(1)
            device = match.group(2)
            log.debug(u'Found NMJ database {0} on device {1}', database, device)
            app.NMJ_DATABASE = database
        else:
            log.warning(u'Could not get current NMJ database on {0}, NMJ is probably not running!', host)
            return False

        # if the device is a remote host then try to parse the mounting URL and save it to the config
        if device.startswith('NETWORK_SHARE/'):
            match = re.search('.*(?=\r\n?%s)' % (re.escape(device[14:])), tnoutput)

            if match:
                mount = match.group().replace('127.0.0.1', host)
                log.debug(u'Found mounting url on the Popcorn Hour in configuration: {0}', mount)
                app.NMJ_MOUNT = mount
            else:
                log.warning(u'Detected a network share on the Popcorn Hour, but could not get the mounting url')
                return False

        return True

    def notify_snatch(self, title, message):
        return False
        # Not implemented: Start the scanner when snatched does not make any sense

    def notify_download(self, ep_obj):
        if app.USE_NMJ:
            self._notifyNMJ()

    def notify_subtitle_download(self, ep_obj, lang):
        if app.USE_NMJ:
            self._notifyNMJ()

    def notify_git_update(self, new_version):
        return False
        # Not implemented, no reason to start scanner.

    def notify_login(self, ipaddress=''):
        return False

    def test_notify(self, host, database, mount):
        return self._sendNMJ(host, database, mount)

    def _sendNMJ(self, host, database, mount=None):
        """
        Send a NMJ update command to the specified machine

        host: The hostname/IP to send the request to (no port)
        database: The database to send the request to
        mount: The mount URL to use (optional)

        return: True if the request succeeded, False otherwise
        """

        # if a mount URL is provided then attempt to open a handle to that URL
        if mount:
            try:
                req = Request(mount)
                log.debug(u'Try to mount network drive via url: {0}', mount)
                handle = urlopen(req)
            except IOError as error:
                if hasattr(error, 'reason'):
                    log.warning(u'NMJ: Could not contact Popcorn Hour on host {0}: {1}', host, error.reason)
                elif hasattr(error, 'code'):
                    log.warning(u'NMJ: Problem with Popcorn Hour on host {0}: {1}', host, error.code)
                return False
            except Exception as error:
                log.error(u'NMJ: Unknown exception: {0}', ex(error))
                return False

        # build up the request URL and parameters
        UPDATE_URL = 'http://%(host)s:8008/metadata_database?%(params)s'
        params = {
            'arg0': 'scanner_start',
            'arg1': database,
            'arg2': 'background',
            'arg3': ''
        }
        params = urlencode(params)
        updateUrl = UPDATE_URL % {'host': host, 'params': params}

        # send the request to the server
        try:
            req = Request(updateUrl)
            log.debug(u'Sending NMJ scan update command via url: {0}', updateUrl)
            handle = urlopen(req)
            response = handle.read()
        except IOError as error:
            if hasattr(error, 'reason'):
                log.warning(u'NMJ: Could not contact Popcorn Hour on host {0}: {1}', host, error.reason)
            elif hasattr(error, 'code'):
                log.warning(u'NMJ: Problem with Popcorn Hour on host {0}: {1}', host, error.code)
            return False
        except Exception as error:
            log.error(u'NMJ: Unknown exception: {0}', ex(error))
            return False

        # try to parse the resulting XML
        try:
            et = etree.fromstring(response)
            result = et.findtext('returnValue')
        except SyntaxError as error:
            log.error(u'Unable to parse XML returned from the Popcorn Hour: {0}', error)
            return False

        # if the result was a number then consider that an error
        if int(result) > 0:
            log.error(u'Popcorn Hour returned an error code: {0!r}', result)
            return False
        else:
            log.info(u'NMJ started background scan')
            return True

    def _notifyNMJ(self, host=None, database=None, mount=None, force=False):
        """
        Sends a NMJ update command based on the SB config settings

        host: The host to send the command to (optional, defaults to the host in the config)
        database: The database to use (optional, defaults to the database in the config)
        mount: The mount URL (optional, defaults to the mount URL in the config)
        force: If True then the notification will be sent even if NMJ is disabled in the config
        """
        if not app.USE_NMJ and not force:
            log.debug(u'Notification for NMJ scan update not enabled, skipping this notification')
            return False

        # fill in omitted parameters
        if not host:
            host = app.NMJ_HOST
        if not database:
            database = app.NMJ_DATABASE
        if not mount:
            mount = app.NMJ_MOUNT

        log.debug(u'Sending scan command for NMJ ')

        return self._sendNMJ(host, database, mount)
