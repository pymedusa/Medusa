# coding=utf-8

from __future__ import unicode_literals

import logging

from feedparser.api import parse

from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def getFeed(url, params=None, request_hook=None):
    try:
        response = request_hook(url, params=params, timeout=30)
        if not response:
            raise Exception

        feed = parse(response.text, response_headers={'content-type': 'application/xml'})
        if feed:
            if 'entries' in feed:
                return feed
            elif 'error' in feed.feed:
                err_code = feed.feed['error']['code']
                err_desc = feed.feed['error']['description']
                log.debug(u'RSS ERROR:[{error}] CODE:[{code}]',
                          {'error': err_desc, 'code': err_code})
        else:
            log.debug(u'RSS error loading data: {}', url)

    except Exception as e:
        log.debug(u'RSS error: {}', ex(e))

    return {'entries': []}
