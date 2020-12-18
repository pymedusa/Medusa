# coding: utf-8

"""
Copyright 2015 SmartBear Software

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

Credit: this file (rest.py) is modified based on rest.py in Dropbox Python SDK:
https://www.dropbox.com/developers/core/sdks/python
"""
from __future__ import absolute_import, unicode_literals

import logging

from requests.exceptions import RequestException

from six import text_type

from .exceptions import ApiException

logger = logging.getLogger(__name__)


class RESTClientObject(object):

    def __init__(self, session):
        self.session = session

    def request(self, method, url, query_params=None, headers=None, body=None, post_params=None):

        try:
            # For `POST`, `PUT`, `PATCH`, `OPTIONS`
            if method in ['POST', 'PUT', 'PATCH', 'OPTIONS']:
                if headers['Content-Type'] == 'application/json':
                    r = self.session.request(method, url, params=query_params, headers=headers, json=body)
                if headers['Content-Type'] == 'application/x-www-form-urlencoded':
                    r = self.session.request(method, url, params=query_params, headers=headers, json=post_params)
                if headers['Content-Type'] == 'multipart/form-data':
                    r = self.session.request(method, url, params=query_params, headers=headers)
            # For `GET`, `HEAD`, `DELETE`
            else:
                r = self.session.request(method, url, params=query_params, headers=headers)

            r.raise_for_status()

        except RequestException as error:
            status = 0
            msg = "{0}\n{1}".format(type(error).__name__, text_type(error))
            try:
                status = error.response.status_code
            except AttributeError:
                pass
            raise ApiException(status=status, reason=msg)
        else:
            return r

    def get(self, url, headers=None, query_params=None):
        return self.request("GET", url,
                            headers=headers,
                            query_params=query_params)

    def head(self, url, headers=None, query_params=None):
        return self.request("HEAD", url,
                            headers=headers,
                            query_params=query_params)

    def options(self, url, headers=None, query_params=None, post_params=None, body=None):
        return self.request("OPTIONS", url,
                            headers=headers,
                            query_params=query_params,
                            post_params=post_params,
                            body=body)

    def delete(self, url, headers=None, query_params=None):
        return self.request("DELETE", url,
                            headers=headers,
                            query_params=query_params)

    def post(self, url, headers=None, query_params=None, post_params=None, body=None):
        return self.request("POST", url,
                            headers=headers,
                            query_params=query_params,
                            post_params=post_params,
                            body=body)

    def put(self, url, headers=None, query_params=None, post_params=None, body=None):
        return self.request("PUT", url,
                            headers=headers,
                            query_params=query_params,
                            post_params=post_params,
                            body=body)

    def patch(self, url, headers=None, query_params=None, post_params=None, body=None):
        return self.request("PATCH", url,
                            headers=headers,
                            query_params=query_params,
                            post_params=post_params,
                            body=body)
