# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

import guessit

from medusa.server.api.v2.base import BaseRequestHandler


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

        guess = guessit.guessit(release)

        return self._ok(data=dict(guess))
