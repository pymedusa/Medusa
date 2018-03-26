# coding=utf-8

from __future__ import unicode_literals

import logging

import cfscrape

from medusa.logger.adapters.style import BraceAdapter

import requests
from requests.utils import dict_from_cookiejar

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def log_url(response, **kwargs):
    """Response hook to log request URL."""
    request = response.request
    log.debug(
        '{method} URL: {url} [Status: {status}]', {
            'method': request.method,
            'url': request.url,
            'status': response.status_code,
        }
    )
    log.debug('User-Agent: {}'.format(request.headers['User-Agent']))

    if request.method.upper() == 'POST':
        if request.body:
            if 'multipart/form-data' not in request.headers.get('content-type', ''):
                body = request.body
            else:
                body = request.body[1:99].replace('\n', ' ') + '...'
        else:
            body = ''

        # try to log post data using various codecs to decode
        if isinstance(body, text_type):
            log.debug('With post data: {0}', body)
            return

        codecs = ('utf-8', 'latin1', 'cp1252')
        for codec in codecs:
            try:
                data = body.decode(codec)
            except UnicodeError as error:
                log.debug('Failed to decode post data as {codec}: {msg}',
                          {'codec': codec, 'msg': error})
            else:
                log.debug('With post data: {0}', data)
                break
        else:
            log.warning('Failed to decode post data with {codecs}',
                        {'codecs': codecs})


def cloudflare(resp, **kwargs):
    """
    Bypass CloudFlare's anti-bot protection.

    A response hook that retries a request after bypassing CloudFlare anti-bot
    protection.  Use the sessioned hook factory to attach the session to the
    response to persist CloudFlare authentication at the session level.
    """
    if is_cloudflare_challenge(resp):

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
    """Hooks factory to add a session to a response."""
    def sessioned_response_hook(response, *args, **kwargs):
        """Return a sessioned response."""
        response.session = session
        return response
    return sessioned_response_hook


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
