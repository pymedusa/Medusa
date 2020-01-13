# coding=utf-8

from __future__ import unicode_literals

import errno
import logging
import traceback

import certifi

import medusa.common
from medusa import app
from medusa.session import factory, handlers, hooks

import requests

from six.moves import collections_abc

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class BaseSession(requests.Session):
    """Base Session object.

    This is a Medusa base session, used to create and configure a session object with Medusa specific base
    values.
    """

    default_headers = {
        'User-Agent': medusa.common.USER_AGENT,
        'Accept-Encoding': 'gzip,deflate',
    }


class MedusaSession(BaseSession):
    """Medusa default Session object.

    This is a Medusa base session, used to create and configure a session object with Medusa specific base
    values.

    :param verify: Enable/Disable SSL certificate verification.
    :param proxies: Provide a proxy configuration in the form of a dict: {
        "http": address,
        "https": address,
    }
    Optional arguments:
    :param hooks: Provide additional 'response' hooks, provided as a list of functions.
    :cache_control: Provide a cache control dict of cache_control options.
    :example: {'cache_etags': True, 'serializer': None, 'heuristic': None}
    :return: The response as text or False.
    """

    @staticmethod
    def _get_ssl_cert(verify):
        """
        Configure the ssl verification.

        We need to overwrite this in the request method. As it's not available in the session init.

        :param verify: SSL verification on or off.
        """
        if all([app.SSL_VERIFY, verify]):
            if app.SSL_CA_BUNDLE:
                return app.SSL_CA_BUNDLE
            else:
                return certifi.where()

        return False

    def __init__(self, proxies=None, **kwargs):
        """Create base Medusa session instance."""
        # Add response hooks
        self.my_hooks = kwargs.pop('hooks', [])

        # Pop the cache_control config
        cache_control = kwargs.pop('cache_control', None)

        # Apply handler for bypassing CloudFlare protection
        self.cloudflare = kwargs.pop('cloudflare', False)

        # Initialize request.session after we've done the pop's.
        super(MedusaSession, self).__init__(**kwargs)

        # Add cache control of provided as a dict. Needs to be attached after super init.
        if cache_control:
            factory.add_cache_control(self, cache_control)

        # add proxies
        self.proxies = proxies or factory.add_proxies()

        # Configure global session hooks
        self.hooks['response'].append(hooks.log_url)

        # Extend the hooks with kwargs provided session hooks
        self.hooks['response'].extend(self.my_hooks)

        # Set default headers.
        self.headers.update(self.default_headers)

    def request(self, method, url, data=None, params=None, headers=None, timeout=30, verify=True, **kwargs):
        ssl_cert = self._get_ssl_cert(verify)
        response = super(MedusaSession, self).request(method, url, data=data, params=params, headers=headers,
                                                      timeout=timeout, verify=ssl_cert, **kwargs)
        if self.cloudflare:
            response = handlers.cloudflare(self, response, timeout=timeout, verify=ssl_cert, **kwargs)

        return response

    def get_json(self, url, method='GET', *args, **kwargs):
        """Overwrite request, to be able to return the json value if possible. Else it will fail silently."""
        resp = self.request(method, url, *args, **kwargs)
        try:
            return resp.json() if resp else resp
        except ValueError:
            return None

    def get_content(self, url, method='GET', *args, **kwargs):
        """Overwrite request, to be able to return the content if possible. Else it will fail silently."""
        resp = self.request(method, url, *args, **kwargs)
        return resp.content if resp else resp

    def get_text(self, url, method='GET', *args, **kwargs):
        """Overwrite request, to be able to return the text value if possible. Else it will fail silently."""
        resp = self.request(method, url, *args, **kwargs)
        return resp.text if resp else resp


class MedusaSafeSession(MedusaSession):
    """Medusa Safe Session object.

    This is a Medusa safe session object, used to create and configure a session protected with the most common
    exception handling.

    :param verify: Enable/Disable SSL certificate verification.
    :param proxies: Provide a proxy configuration in the form of a dict: {
        "http": address,
        "https": address,
    }
    Optional arguments:
    :param hooks: Provide additional 'response' hooks, provided as a list of functions.
    :cache_control: Provide a cache control dict of cache_control options.
    :example: {'cache_etags': True, 'serializer': None, 'heuristic': None}
    :return: The response as text or False.
    """

    def __init__(self, *args, **kwargs):
        # Initialize request.session
        super(MedusaSafeSession, self).__init__(**kwargs)

    def request(self, method, url, data=None, params=None, headers=None, timeout=30, verify=True, **kwargs):
        """Overwrite request, for adding basic exception handling."""
        resp = None
        try:
            resp = super(MedusaSafeSession, self).request(method, url, data=data, params=params, headers=headers,
                                                          timeout=timeout, verify=verify, **kwargs)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as error:
            log.debug(u'The response returned a non-200 response while requesting url {url} Error: {err_msg!r}',
                      url=url, err_msg=error)
            return resp or error.response
        except requests.exceptions.RequestException as error:
            log.debug(u'Error requesting url {url} Error: {err_msg}', url=url, err_msg=error)
            return resp or error.response
        except Exception as error:
            if ((isinstance(error, collections_abc.Iterable) and u'ECONNRESET' in error) or
                    (hasattr(error, u'errno') and error.errno == errno.ECONNRESET)):
                log.warning(
                    u'Connection reset by peer accessing url {url} Error: {err_msg}'.format(url=url, err_msg=error)
                )
            else:
                log.info(u'Unknown exception in url {url} Error: {err_msg}', url=url, err_msg=error)
                log.debug(traceback.format_exc())
            return None

        return resp
