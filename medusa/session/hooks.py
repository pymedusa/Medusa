# coding=utf-8

from __future__ import unicode_literals

import logging

import cfscrape
import requests
from requests.utils import dict_from_cookiejar

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def log_url(resp, **kwargs):
    """Response hook to log request URL."""
    log.debug(
        '{method} URL: {url} [Status: {status}]'.format(
            method=resp.request.method,
            url=resp.request.url,
            status=resp.status_code,
        )
    )
    log.debug('User-Agent: {}'.format(resp.request.headers['User-Agent']))

    if resp.request.method.upper() == 'POST':
        log.debug('With post data: {data}'.format(data=resp.request.body))

    return resp


def cloudflare(resp, **kwargs):
    """
    Bypass CloudFlare's anti-bot protection.

    A response hook that retries a request after bypassing CloudFlare anti-bot
    protection.  Use the sessioned hook factory to attach the session to the
    response to persist CloudFlare authentication at the session level.
    """
    if all([resp.status_code == 503,  # Service unavailable
            resp.headers.get('server') == u'cloudflare-nginx', ]):

        log.debug(u'CloudFlare protection detected, trying to bypass it')

        # Get the session used or create a new one
        session = getattr(resp, 'session', requests.Session())

        # Get the original request
        original_request = resp.request

        # Avoid recursion by removing the hook from the original request
        original_request.hooks['response'].remove(cloudflare)

        # Get the CloudFlare tokens and original user-agent
        tokens, user_agent = cfscrape.get_tokens(original_request.url)

        # Add CloudFlare tokens to the session cookies
        session.cookies.update(tokens)
        # Add CloudFlare Tokens to the original request
        original_cookies = dict_from_cookiejar(original_request._cookies)
        original_cookies.update(tokens)
        original_request.prepare_cookies(original_cookies)

        # The same User-Agent must be used for the retry
        # Update the session with the CloudFlare User-Agent
        session.headers['User-Agent'] = user_agent
        # Update the original request with the CloudFlare User-Agent
        original_request.headers['User-Agent'] = user_agent

        # Resend the request
        cf_resp = session.send(
            original_request,
            allow_redirects=True,
            **kwargs
        )

        if cf_resp.ok:
            log.debug('CloudFlare successfully bypassed.')
        return cf_resp
    else:
        return resp


def sessioned(session):
    """
    Hook factory to add a session to a response.
    """
    def sessioned_response_hook(response, *args, **kwargs):
        """
        Returns a sessioned response.
        """
        response.session = session
        return response
    return sessioned_response_hook
