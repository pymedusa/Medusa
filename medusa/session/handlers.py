# coding=utf-8

"""Define custom response handlers - custom hooks with access to the session object."""

from __future__ import unicode_literals

import logging

from cloudscraper import CloudScraper

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
    Bypass Cloudflare's anti-bot protection.

    A request handler that retries a request after bypassing Cloudflare anti-bot
    protection.
    """
    if CloudScraper.is_IUAM_Challenge(resp) or CloudScraper.is_Captcha_Challenge(resp):
        log.debug('Cloudflare protection detected, trying to bypass it.')

        # Get the original request
        original_request = resp.request

        # Get the Cloudflare tokens and original user-agent
        tokens, user_agent = CloudScraper.get_tokens(original_request.url)

        # Add Cloudflare tokens to the session cookies
        session.cookies.update(tokens)
        # Add Cloudflare Tokens to the original request
        original_cookies = dict_from_cookiejar(original_request._cookies)
        original_cookies.update(tokens)
        original_request.prepare_cookies(original_cookies)

        # The same User-Agent must be used for the retry
        # Update the session with the Cloudflare User-Agent
        session.headers['User-Agent'] = user_agent
        # Update the original request with the Cloudflare User-Agent
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
            log.debug('Cloudflare successfully bypassed.')
        return cf_resp
    else:
        if (CloudScraper.is_New_IUAM_Challenge(resp) or CloudScraper.is_Firewall_Blocked(resp)
                or CloudScraper.is_New_Captcha_Challenge(resp)):
            log.warning("Cloudflare captcha challenge v2 or firewall detected, it can't be bypassed.")
        return resp
