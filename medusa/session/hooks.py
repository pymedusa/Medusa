# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa.logger.adapters.style import BraceAdapter

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
