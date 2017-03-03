# coding=utf-8

import logging

from feedparser.api import parse

from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)
log = BraceAdapter(log)


def getFeed(url, params=None, request_hook=None):
    try:
        data = request_hook(url, params=params, returns='text', timeout=30)
        if not data:
            raise Exception

        feed = parse(data, response_headers={'content-type': 'application/xml'})
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
