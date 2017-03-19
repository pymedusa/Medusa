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
from __future__ import absolute_import

import io
import logging
from requests.exceptions import RequestException


logger = logging.getLogger(__name__)


class RESTResponse(io.IOBase):

    def __init__(self, resp):
        self.requests_response = resp
        self.status = resp.status_code
        self.reason = resp.reason
        self.data = resp.content

    def getheaders(self):
        """
        Returns a dictionary of the response headers.
        """
        return self.requests_response.headers

    def getheader(self, name, default=None):
        """
        Returns a given response header.
        """
        return self.requests_response.headers.get(name, default)


class RESTClientObject(object):

    def __init__(self, session=None):
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

        except RequestException as e:
            msg = "{0}\n{1}".format(type(e).__name__, str(e))
            raise ApiException(status=0, reason=msg)

        r = RESTResponse(r)

        # log response body
        logger.debug("response body: %s" % r.data)

        if r.status not in range(200, 206):
            raise ApiException(http_resp=r)

        return r

    def GET(self, url, headers=None, query_params=None):
        return self.request("GET", url,
                            headers=headers,
                            query_params=query_params)

    def HEAD(self, url, headers=None, query_params=None):
        return self.request("HEAD", url,
                            headers=headers,
                            query_params=query_params)

    def OPTIONS(self, url, headers=None, query_params=None, post_params=None, body=None):
        return self.request("OPTIONS", url,
                            headers=headers,
                            query_params=query_params,
                            post_params=post_params,
                            body=body)

    def DELETE(self, url, headers=None, query_params=None):
        return self.request("DELETE", url,
                            headers=headers,
                            query_params=query_params)

    def POST(self, url, headers=None, query_params=None, post_params=None, body=None):
        return self.request("POST", url,
                            headers=headers,
                            query_params=query_params,
                            post_params=post_params,
                            body=body)

    def PUT(self, url, headers=None, query_params=None, post_params=None, body=None):
        return self.request("PUT", url,
                            headers=headers,
                            query_params=query_params,
                            post_params=post_params,
                            body=body)

    def PATCH(self, url, headers=None, query_params=None, post_params=None, body=None):
        return self.request("PATCH", url,
                            headers=headers,
                            query_params=query_params,
                            post_params=post_params,
                            body=body)


class ApiException(Exception):

    def __init__(self, status=None, reason=None, http_resp=None):
        if http_resp:
            self.status = http_resp.status
            self.reason = http_resp.reason
            self.body = http_resp.data
            self.headers = http_resp.getheaders()
        else:
            self.status = status
            self.reason = reason
            self.body = None
            self.headers = None

    def __str__(self):
        """
        Custom error messages for exception
        """
        error_message = "({0})\n"\
                        "Reason: {1}\n".format(self.status, self.reason)
        if self.headers:
            error_message += "HTTP response headers: {0}\n".format(self.headers)

        if self.body:
            error_message += "HTTP response body: {0}\n".format(self.body)

        return error_message
