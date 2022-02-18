# coding=utf-8

"""
Synology Download Station Client.

Uses the Synology Download Station API:
http://download.synology.com/download/Document/DeveloperGuide/Synology_Download_Station_Web_API.pdf
"""

from __future__ import unicode_literals

import logging
import os
import re

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DownloadStationAPI(GenericClient):
    """Synology Download Station API class."""

    def __init__(self, host=None, username=None, password=None, torrent_path=None):
        """Downloadstationapi constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(DownloadStationAPI, self).__init__('DownloadStation', host, username, password, torrent_path)
        self.error_map = {
            100: 'Unknown error',
            101: 'Invalid parameter',
            102: 'The requested API does not exist',
            103: 'The requested method does not exist',
            104: 'The requested version does not support the functionality',
            105: 'The logged in session does not have permission',
            106: 'Session timeout',
            107: 'Session interrupted by duplicate login',
            119: 'SID not found',
            120: 'Wrong parameter',
            400: 'File upload failed',
            401: 'Max number of tasks reached',
            402: 'Destination denied',
            403: 'Destination does not exist',
            404: 'Invalid task id',
            405: 'Invalid task action',
            406: 'No default destination',
            407: 'Set destination failed',
            408: 'File does not exist'
        }
        self.url = self.host
        app.TORRENT_PATH = re.sub(r'^/volume\d*/', '', app.TORRENT_PATH)

        self._get_auth()

    def _check_path(self):
        """Validate the destination."""
        if not self.torrent_path:
            return True
        log.info('{name} checking if "{torrent_path}" is a valid share', {
            'name': self.name, 'torrent_path': self.torrent_path
        })
        self.url = urljoin(self.host, 'webapi/entry.cgi')
        params = {
            'api': 'SYNO.Core.Share',
            'version': 1,
            'method': 'list'
        }

        # Get all available shares from DSM)
        if not self._request(method='get', params=params):
            return False
        jdata = self.response.json()
        if not jdata['success']:
            err_code = jdata.get('error', {}).get('code', 100)
            self.message = f'Could not get the list of shares from {self.name}: {self.error_map[err_code]}'
            log.warning(self.message)
            return False

            # Walk through the available shares and check if the path is a valid share (if present we remove the volume name).
        for share in jdata.get('data', {}).get('shares', ''):
            if self.torrent_path.startswith(f"{share['vol_path']}/{share['name']}"):
                fullpath = self.torrent_path
                self.torrent_path = fullpath.replace(f"{share['vol_path']}/", '')
                break
            elif self.torrent_path.lstrip('/').startswith(f"{share['name']}"):
                self.torrent_path = self.torrent_path.lstrip('/')
                fullpath = f"{share['vol_path']}/{self.torrent_path}"
                break
        else:
            # No break occurred, so the destination is not a valid share
            self.message = f'"{self.torrent_path}" is not a valid location'
            return False
        if os.access(fullpath, os.W_OK | os.X_OK):
            return True
        else:
            self.message = f'This user does not have the correct permissions to use "{fullpath}"'
            log.warning(self.message)
            return False

    def _get_auth(self):
        """Downloadstation login."""
        errmap = {
            400: 'No such account or incorrect password',
            401: 'Account disabled',
            402: 'Permission denied',
            403: '2-step verification code required',
            404: 'Failed to authenticate 2-step verification code'
        }
        self.url = urljoin(self.host, 'webapi/auth.cgi')
        params = {
            'method': 'login',
            'api': 'SYNO.API.Auth',
            'version': 3,
            'session': 'DownloadStation',
            'account': self.username,
            'passwd': self.password
        }
        self.auth = True
        if not self._request(method='get', params=params):
            self.auth = False
            return False
        jdata = self.response.json()
        if jdata.get('success'):
            self.auth = True
        else:
            err_code = jdata.get('error', {}).get('code', 100)
            self.message = f'{self.name} login error: {errmap[err_code]}'
            log.warning(self.message)
            self.auth = False
        return self.auth

    def _add_torrent_uri(self, result):
        # parameters "type' and "destination" must be coded as a json string so we add double quotes to those parameters
        params = {
            'api': 'SYNO.DownloadStation2.Task',
            'version': 2,
            'method': 'create',
            'create_list': 'false',
            'destination': f'"{app.TORRENT_PATH}"',
            'type': '"url"',
            'url': result.url
        }
        return self._add_torrent(params)

    def _add_torrent_file(self, result):
        # Parameters "type" and "file" must be individually coded as a json string so we add double quotes to those parameters
        # The "file" paramater (torrent in this case) must corrospondent with the key in the files parameter
        params = {
            'api': 'SYNO.DownloadStation2.Task',
            'version': 2,
            'method': 'create',
            'create_list': 'false',
            'destination': f'"{app.TORRENT_PATH}"',
            'type': '"file"',
            'file': '["torrent"]'
        }
        torrent_file = {'torrent': (f'{result.name}.torrent', result.content)}
        return self._add_torrent(params, torrent_file)

    def _add_torrent(self, params, torrent_file=None):
        """Add a torrent to DownloadStation."""
        self.url = urljoin(app.TORRENT_HOST, 'webapi/entry.cgi')
        if not self._request(method='post', data=params, files=torrent_file):
            return False
        jdata = self.response.json()
        if jdata['success']:
            log.info('Torrent added as task {task_id} to {self_name}', {
                'task_id': jdata['data']['task_id'], 'self_name': self.name
            })
            return True
        log.warning('Add torrent error: {error}', {
            'error': self.error_map[jdata.get('error', {}).get('code', 100)]
        })
        return False


api = DownloadStationAPI
