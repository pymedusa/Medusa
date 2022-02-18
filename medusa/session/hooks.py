# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa.logger.adapters.style import BraceAdapter

from six import ensure_text

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
            text_body = ensure_text(request.body, errors='replace')
            if 'multipart/form-data' not in request.headers.get('content-type', ''):
                body = text_body
            elif len(text_body) > 99:
                body = text_body[0:99].replace('\n', ' ') + '...'
            else:
                body = text_body.replace('\n', ' ')

            log.debug('With post data: {0}', body)
