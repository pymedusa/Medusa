# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

import logging

from medusa.logger.adapters.style import CustomBraceAdapter
from medusa.name_parser.guessit_parser import guessit
from medusa.name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from medusa.name_parser.rules import default_api
from medusa.server.api.v2.base import BaseRequestHandler


log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class GuessitHandler(BaseRequestHandler):
    """Guessit parser request handler."""

    #: resource name
    name = 'guessit'
    #: identifier
    identifier = None
    #: allowed HTTP methods
    allowed_methods = ('GET',)

    def get(self):
        """Use guessit to `guess` a release name.

        Return the result as a dictionary.
        """
        release = self.get_argument('release')
        if not release:
            return self._bad_request('Missing release name to guess')

        result = {'error': None}
        show = None
        parse_result = None

        try:
            parse_result = NameParser().parse(release)
            show = parse_result.series.to_json()
        except InvalidNameException as error:
            log.debug(
                'Not enough information to parse release name into a valid show. '
                'improve naming for: {release}',
                {'release': release})
            result['error'] = str(error)
        except InvalidShowException as error:
            log.debug(
                'Could not match the parsed title to a show in your library for: '
                'Consider adding scene exceptions for {release}',
                {'release': release})
            result['error'] = str(error)

        if parse_result:
            result['parse'] = parse_result.to_dict()
        else:
            result['parse'] = guessit(release, cached=False)
        result['vanillaGuessit'] = default_api.guessit(release)
        result['show'] = show

        return self._ok(data=dict(result))
