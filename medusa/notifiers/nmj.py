# coding=utf-8

from __future__ import unicode_literals

import logging
import re
import socket
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

class SimpleTelnet:
    """Minimal Telnet implementation for Medusa NMJ commands."""
    def __init__(self, host, port=23, timeout=10):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buffer = b""
    def read_until(self, expected=b'# ', timeout=10):
        """Read until expected prompt appears."""
        import time
        start = time.time()
        while expected not in self.buffer:
            if time.time() - start > timeout:
                raise TimeoutError("Timed out waiting for prompt")
            data = self.sock.recv(1024)
            if not data:
                break
            self.buffer += data
        return self.buffer.decode('utf-8', errors='ignore')
    def write(self, cmd):
        """Send a command with CRLF."""
        self.sock.sendall(cmd.encode('utf-8') + b'\n')
    def read_all(self):
        """Read everything remaining on the socket."""
        chunks = []
        while True:
            data = self.sock.recv(4096)
            if not data:
                break
            chunks.append(data)
        return b''.join(chunks).decode('utf-8', errors='ignore')
    def close(self):
        self.sock.close()

class Notifier(object):
    def notify_settings(self, host):
        """
        Retrieve the settings from a NMJ/Popcorn hour

        host: The hostname/IP of the Popcorn Hour server

        return: True if the settings were retrieved successfully, False otherwise
        """
        # establish a terminal session to the PC
        try:
            terminal = SimpleTelnet(host)
        except Exception:
            log.warning('Warning: unable to get a telnet session to %s', host)
            return False
        try:
            log.debug('Connected to %s via telnet', host)
            # Wait for prompt and send commands
            terminal.read_until(b'sh-3.00# ')
            terminal.write('cat /tmp/source')
            terminal.write('cat /tmp/netshare')
            terminal.write('exit')
            tnoutput = terminal.read_all()
        except Exception as e:
            log.warning('Error during Telnet session to %s: %s', host, e)
            return False
        finally:
            terminal.close()  # ensure socket is closed
        # parse database and device
        match = re.search(r'(.+\.db)\r\n?(.+)(?=sh-3.00# cat /tmp/netshare)', tnoutput)
        if match:
            database = match.group(1)
            device = match.group(2)
            log.debug('Found NMJ database %s on device %s', database, device)
            app.NMJ_DATABASE = database
        else:
            log.warning('Could not get current NMJ database on %s, NMJ is probably not running!', host)
            return False
        # parse mount URL if remote
        if device.startswith('NETWORK_SHARE/'):
            match = re.search('.*(?=\r\n?%s)' % (re.escape(device[14:])), tnoutput)
            if match:
                mount = match.group().replace('127.0.0.1', host)
                log.debug('Found mounting URL on the Popcorn Hour: %s', mount)
                app.NMJ_MOUNT = mount
            else:
                log.warning('Detected a network share on the Popcorn Hour, but could not get the mounting URL')
                return False
        return True

    def notify_snatch(self, title, message, **kwargs):
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
