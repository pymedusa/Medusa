# coding=utf-8

from __future__ import unicode_literals

import errno
import logging
import traceback

import certifi

import medusa.common
from medusa.app import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.session import factory, handlers, hooks

import requests

from six.moves import collections_abc
from six.moves.urllib.parse import urlparse


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


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

        # Configure global session hooks
        self.hooks['response'].append(hooks.log_url)

        # Extend the hooks with kwargs provided session hooks
        self.hooks['response'].extend(self.my_hooks)

        # Set default headers.
        self.headers.update(self.default_headers)

    def _add_proxies(self):
        """As we're dependent on medusa app config. We need to set the proxy before the classes are initialized."""
        def get_proxy_setting():
            config = {
                'ProviderSession': app.PROXY_PROVIDERS,
                'IndexerSession': app.PROXY_INDEXERS,
                'ClientSession': app.PROXY_CLIENTS
            }
            if (isinstance(self, (ProviderSession, IndexerSession, ClientSession))):
                return config[self.__class__.__name__]

            return app.PROXY_OTHERS

        if app.PROXY_SETTING and get_proxy_setting():
            log.debug('Using proxy: {proxy} for {class}', {'proxy': app.PROXY_SETTING, 'class': self.__class__.__name__})
            proxy = urlparse(app.PROXY_SETTING)
            address = app.PROXY_SETTING if proxy.scheme else 'http://' + app.PROXY_SETTING
            self.proxies = {
                'http': address,
                'https': address,
            }
        else:
            self.proxies = None

    def request(self, method, url, data=None, params=None, headers=None, timeout=30, verify=True, **kwargs):
        """Medusa session request method."""
        ssl_cert = self._get_ssl_cert(verify)
        self._add_proxies()

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
        """Initialize request.session."""
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
            if ((isinstance(error, collections_abc.Iterable) and u'ECONNRESET' in error)
                    or (hasattr(error, u'errno') and error.errno == errno.ECONNRESET)):
                log.warning(
                    u'Connection reset by peer accessing url {url} Error: {err_msg}'.format(url=url, err_msg=error)
                )
            else:
                log.info(u'Unknown exception in url {url} Error: {err_msg}', url=url, err_msg=error)
                log.debug(traceback.format_exc())
            return None

        return resp


class ProviderSession(MedusaSafeSession):
    """Requests session for providers."""

    def __init__(self, **kwargs):
        """Init super and hook in the proxy if configured for providers."""
        # Initialize request.session
        super(ProviderSession, self).__init__(**kwargs)


class IndexerSession(MedusaSafeSession):
    """Requests session for indexers."""

    def __init__(self, **kwargs):
        """Init super and hook in the proxy if configured for indexers."""
        # Initialize request.session
        super(IndexerSession, self).__init__(**kwargs)


class ClientSession(MedusaSession):
    """Requests session for clients."""

    def __init__(self, **kwargs):
        """Init super and hook in the proxy if configured for clients."""
        # Initialize request.session
        super(ClientSession, self).__init__(**kwargs)
