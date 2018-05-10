# coding=utf-8

"""Define custom response handlers - custom hooks with access to the session object."""

from __future__ import unicode_literals

import logging

import cfscrape

from medusa.logger.adapters.style import BraceAdapter

from requests.utils import dict_from_cookiejar

from six import viewitems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def filtered_kwargs(kwargs):
    """Filter kwargs to only contain arguments accepted by `requests.Session.send`."""
    return {
        k: v for k, v in viewitems(kwargs)
        if k in ('stream', 'timeout', 'verify', 'cert', 'proxies', 'allow_redirects')
    }


def cloudflare(session, resp, **kwargs):
    """
    Bypass CloudFlare's anti-bot protection.

    A request handler that retries a request after bypassing CloudFlare anti-bot
    protection.
    """
    if is_cloudflare_challenge(resp):

        log.debug(u'CloudFlare protection detected, trying to bypass it')

        # Get the original request
        original_request = resp.request

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
        kwargs = filtered_kwargs(kwargs)
        kwargs['allow_redirects'] = True
        cf_resp = session.send(
            original_request,
            **kwargs
        )
        cf_resp.raise_for_status()

        if cf_resp.ok:
            log.debug('CloudFlare successfully bypassed.')
        return cf_resp
    else:
        return resp


def is_cloudflare_challenge(resp):
    """Check if the response is a Cloudflare challange.

    Source: goo.gl/v8FvnD
    """
    return (
        resp.status_code == 503
        and resp.headers.get('Server', '').startswith('cloudflare')
        and b'jschl_vc' in resp.content
        and b'jschl_answer' in resp.content
    )
