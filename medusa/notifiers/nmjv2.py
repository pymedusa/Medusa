# coding=utf-8

from __future__ import unicode_literals

import logging
import time
from xml.dom.minidom import parseString

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

from six.moves.urllib.request import Request, urlopen

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def notify_snatch(self, ep_name, is_proper):  # pylint: disable=unused-argument
        return False
        # Not implemented: Start the scanner when snatched does not make any sense

    def notify_download(self, ep_name):  # pylint: disable=unused-argument
        self._notifyNMJ()

    def notify_subtitle_download(self, ep_name, lang):  # pylint: disable=unused-argument
        self._notifyNMJ()

    def notify_git_update(self, new_version):  # pylint: disable=unused-argument
        return False
        # Not implemented, no reason to start scanner.

    def notify_login(self, ipaddress=''):  # pylint: disable=unused-argument
        return False

    def test_notify(self, host):
        return self._sendNMJ(host)

    def notify_settings(self, host, dbloc, instance):
        """
        Retrieve the NMJv2 database location from Popcorn hour

        host: The hostname/IP of the Popcorn Hour server
        dbloc: 'local' for PCH internal hard drive. 'network' for PCH network shares
        instance: Allows for selection of different DB in case of multiple databases

        return: True if the settings were retrieved successfully, False otherwise
        """
        try:
            url_loc = 'http://{}:8008/file_operation?arg0=list_user_storage_file&arg1=&arg2={}&arg3=20&arg4=true&arg5=true&arg6=true&arg7=all&arg8=name_asc&arg9=false&arg10=false'.format(host, instance)
            req = Request(url_loc)
            handle1 = urlopen(req)
            response1 = handle1.read()
            xml = parseString(response1)
            time.sleep(0.3)
            for node in xml.getElementsByTagName('path'):
                xmlTag = node.toxml()
                xmlData = xmlTag.replace('<path>', '').replace('</path>', '').replace('[=]', '')
                url_db = 'http://' + host + ':8008/metadata_database?arg0=check_database&arg1=' + xmlData
                reqdb = Request(url_db)
                handledb = urlopen(reqdb)
                responsedb = handledb.read()
                xmldb = parseString(responsedb)
                returnvalue = xmldb.getElementsByTagName('returnValue')[0].toxml().replace('<returnValue>', '').replace(
                    '</returnValue>', '')
                if returnvalue == '0':
                    DB_path = xmldb.getElementsByTagName('database_path')[0].toxml().replace(
                        '<database_path>', '').replace('</database_path>', '').replace('[=]', '')
                    if dbloc == 'local' and DB_path.find('localhost') > -1:
                        app.NMJv2_HOST = host
                        app.NMJv2_DATABASE = DB_path
                        return True
                    if dbloc == 'network' and DB_path.find('://') > -1:
                        app.NMJv2_HOST = host
                        app.NMJv2_DATABASE = DB_path
                        return True

        except IOError as e:
            log.warning(u'Warning: Unable to contact popcorn hour on host {0}: {1}', host, e)
            return False
        return False

    def _sendNMJ(self, host):
        """
        Send a NMJ update command to the specified machine

        host: The hostname/IP to send the request to (no port)
        database: The database to send the request to
        mount: The mount URL to use (optional)

        return: True if the request succeeded, False otherwise
        """
        # if a host is provided then attempt to open a handle to that URL
        try:
            url_scandir = 'http://' + host + ':8008/metadata_database?arg0=update_scandir&arg1=' + app.NMJv2_DATABASE + '&arg2=&arg3=update_all'
            log.debug(u'NMJ scan update command sent to host: {0}', host)
            url_updatedb = 'http://' + host + ':8008/metadata_database?arg0=scanner_start&arg1=' + app.NMJv2_DATABASE + '&arg2=background&arg3='
            log.debug(u'Try to mount network drive via url: {0}', host)
            prereq = Request(url_scandir)
            req = Request(url_updatedb)
            handle1 = urlopen(prereq)
            response1 = handle1.read()
            time.sleep(0.3)
            handle2 = urlopen(req)
            response2 = handle2.read()
        except IOError as error:
            log.warning(u'Warning: Unable to contact popcorn hour on host {0}: {1}', host, error)
            return False
        try:
            et = etree.fromstring(response1)
            result1 = et.findtext('returnValue')
        except SyntaxError as error:
            log.error(u'Unable to parse XML returned from the Popcorn Hour: update_scandir, {0}', error)
            return False
        try:
            et = etree.fromstring(response2)
            result2 = et.findtext('returnValue')
        except SyntaxError as error:
            log.error(u'Unable to parse XML returned from the Popcorn Hour: scanner_start, {0}', error)
            return False

        # if the result was a number then consider that an error
        error_codes = ['8', '11', '22', '49', '50', '51', '60']
        error_messages = ['Invalid parameter(s)/argument(s)',
                          'Invalid database path',
                          'Insufficient size',
                          'Database write error',
                          'Database read error',
                          'Open fifo pipe failed',
                          'Read only file system']
        if int(result1) > 0:
            index = error_codes.index(result1)
            log.error(u'Popcorn Hour returned an error: {0}', error_messages[index])
            return False
        else:
            if int(result2) > 0:
                index = error_codes.index(result2)
                log.error(u'Popcorn Hour returned an error: {0}', error_messages[index])
                return False
            else:
                log.info(u'NMJv2 started background scan')
                return True

    def _notifyNMJ(self, host=None, force=False):
        """
        Sends a NMJ update command based on the SB config settings

        host: The host to send the command to (optional, defaults to the host in the config)
        database: The database to use (optional, defaults to the database in the config)
        mount: The mount URL (optional, defaults to the mount URL in the config)
        force: If True then the notification will be sent even if NMJ is disabled in the config
        """
        if not app.USE_NMJv2 and not force:
            log.debug(u'Notification for NMJ scan update not enabled, skipping this notification')
            return False

        # fill in omitted parameters
        if not host:
            host = app.NMJv2_HOST

        log.debug(u'Sending scan command for NMJ')

        return self._sendNMJ(host)
