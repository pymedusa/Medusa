# coding=utf-8

"""MLDonkey Client."""

from __future__ import unicode_literals

from medusa.clients.torrent.generic import GenericClient


class MLNetAPI(GenericClient):
    """MLDonkey API class."""

    def __init__(self, host=None, username=None, password=None):
        """Constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(MLNetAPI, self).__init__('mlnet', host, username, password)
        self.url = self.host
        # self.session.auth = HTTPDigestAuth(self.username, self.password);

    def _get_auth(self):

        try:
            self.response = self.session.get(self.host, verify=False)
            self.auth = self.response.content
        except Exception:
            return None

        return self.auth if not self.response.status_code == 404 else None

    def _add_torrent_uri(self, result):

        self.url = '{host}submit'.format(host=self.host)
        params = {
            'q': 'dllink {url}'.format(url=result.url),
        }
        return self._request(method='get', params=params)

    def _add_torrent_file(self, result):

        self.url = '{host}submit'.format(host=self.host)
        params = {
            'q': 'dllink {url}'.format(url=result.url),
        }
        return self._request(method='get', params=params)


api = MLNetAPI
