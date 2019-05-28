# coding=utf-8
"""Request handler for logs."""
from __future__ import unicode_literals

import json
import logging
from datetime import datetime, timedelta

from medusa.logger import LOGGING_LEVELS, filter_logline, read_loglines
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import BaseRequestHandler

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


valid_thread_names = [
    '',
    'BACKLOG',
    'CHECKVERSION',
    'DAILYSEARCHER',
    'ERROR',
    'EVENT',
    'FINDPROPERS',
    'FINDSUBTITLES',
    'MAIN',
    'POSTPROCESSOR',
    'SEARCHQUEUE',
    'SEARCHQUEUE-BACKLOG',
    'SEARCHQUEUE-DAILY-SEARCH',
    'SEARCHQUEUE-FORCED',
    'SEARCHQUEUE-MANUAL',
    'SEARCHQUEUE-RETRY',
    'SEARCHQUEUE-RSS',
    'SHOWQUEUE',
    'SHOWQUEUE-REFRESH',
    'SHOWQUEUE-SEASON-UPDATE',
    'SHOWQUEUE-UPDATE',
    'SHOWUPDATER',
    'Thread',
    'TORNADO',
    'TORRENTCHECKER',
    'TRAKTCHECKER',
]

multi_thread_names = {
    'SHOWQUEUE': {name for name in valid_thread_names if name and name.startswith('SHOWQUEUE-')},
    'SEARCHQUEUE': {name for name in valid_thread_names if name and name.startswith('SEARCHQUEUE-')},
}

log_periods = {
    'all': None,
    'one_day': 1,
    'three_days': 3,
    'one_week': 7,
}


class LogHandler(BaseRequestHandler):
    """Log request handler."""

    #: resource name
    name = 'log'
    #: identifier
    identifier = None
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', )

    def get(self):
        """Query logs."""
        log_level = self.get_argument('level', 'INFO').upper()
        if log_level not in LOGGING_LEVELS:
            return self._bad_request('Invalid log level')

        thread_name = self.get_argument('thread', '').upper()
        if thread_name not in valid_thread_names:
            return self._bad_request('Invalid thread name {0}'.format(thread_name))
        thread_name = multi_thread_names.get(thread_name, thread_name) or None

        try:
            period = log_periods.get(self.get_argument('period', 'all'))
        except KeyError:
            return self._bad_request('Invalid period {0}'.format(period))
        modification_time = datetime.now() - timedelta(days=period) if period else None

        search_query = self.get_argument('query', '') or None
        raw_text = self._parse_boolean(self.get_argument('raw', False))

        arg_page = self._get_page()
        arg_limit = self._get_limit(default=50)
        min_level = LOGGING_LEVELS[log_level]

        def data_generator():
            """Read log lines based on the specified criteria."""
            start = arg_limit * (arg_page - 1) + 1
            reader_kwargs = dict(
                modification_time=modification_time,
                start_index=start,
                max_lines=arg_limit * arg_page,
                predicate=lambda li: filter_logline(
                    li,
                    min_level=min_level,
                    thread_name=thread_name,
                    search_query=search_query
                ),
            )

            for line in read_loglines(**reader_kwargs):
                yield line.to_json() if not raw_text else text_type(line)

        if not raw_text:
            return self._paginate(data_generator=data_generator)
        else:
            text = '\n'.join(data_generator())
            return self._ok(stream=text, content_type='text/plain')

    def post(self):
        """Create a log line.

        By definition this method is NOT idempotent.
        """
        data = json.loads(self.request.body)
        if not data or not all([data.get('message')]):
            return self._bad_request('Invalid request')

        data['level'] = data.get('level', 'INFO').upper()
        if data['level'] not in LOGGING_LEVELS:
            return self._bad_request('Invalid log level')

        message = data['message']
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        level = LOGGING_LEVELS[data['level']]
        log.log(level, message, exc_info=False, *args, **kwargs)
        return self._created()
