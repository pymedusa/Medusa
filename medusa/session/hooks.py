# coding=utf-8

from __future__ import unicode_literals

import logging

import cfscrape
import requests
from requests.utils import dict_from_cookiejar

from medusa.helper.common import http_code_description

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def log_url(r, **kwargs):
    """Response hook to log request URL."""
    log.debug(
        '{method} URL: {url} [Status: {status}]'.format(
            method=r.request.method,
            url=r.request.url,
            status=r.status_code,
        )
    )

    if r.request.method.upper() == 'POST':
        log.debug('With post data: {data}'.format(data=r.request.body))


def cloudflare(r, **kwargs):
    """Try to bypass CloudFlare's anti-bot protection."""
    if all([r.status_code == 503,
            r.headers.get('server') == u'cloudflare-nginx']):
        log.debug(u'CloudFlare protection detected, trying to bypass it')

        try:
            tokens, user_agent = cfscrape.get_tokens(r.request.url)
            cookies = dict_from_cookiejar(r.request._cookies)
            if tokens:
                cookies.update(tokens)

            r.request.headers.update({u'User-Agent': user_agent})
            log.debug(u'CloudFlare protection successfully bypassed.')

            # Disable the hooks, to prevent a loop.
            r.request.hooks = {}

            new_session = requests.Session()
            r.request.prepare_cookies(cookies)
            cf_resp = new_session.send(r.request,
                                       stream=kwargs.get('stream'),
                                       verify=kwargs.get('verify'),
                                       proxies=kwargs.get('proxies'),
                                       timeout=kwargs.get('timeout'),
                                       allow_redirects=True)

            if cf_resp.ok:
                return cf_resp

        except (ValueError, AttributeError) as error:
            log.warning(
                u'Failed to bypass CloudFlare anti-bot protection.'
                u' Error: {err_msg}',
                err_msg=error
            )
            return

    log.debug(
        u'Requested url {url} returned status code {status}: {desc}'.format
        (url=r.url, status=r.status_code,
         desc=http_code_description(r.status_code)))
