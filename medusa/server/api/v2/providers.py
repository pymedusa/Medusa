# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging
from datetime import datetime

from dateutil import parser

from medusa import providers
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import (
    BaseRequestHandler,
)


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ProvidersHandler(BaseRequestHandler):
    """Providers request handler."""

    #: resource name
    name = 'providers'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', 'PATCH', 'DELETE', )

    def get(self, identifier, path_param=None):
        """
        Query provider information.

        Return a list of provider id's.

        :param identifier: provider id. E.g.: myawesomeprovider
        :param path_param:
        """
        show_slug = self._parse(self.get_argument('showslug', default=None), str)
        season = self._parse(self.get_argument('season', default=None), str)
        episode = self._parse(self.get_argument('episode', default=None), str)

        if not identifier:
            # return a list of provider id's
            provider_list = providers.sorted_provider_list()
            return self._ok([provider.to_json() for provider in provider_list])

        provider = providers.get_provider_class(identifier)
        if not provider:
            return self._not_found('Provider not found')

        if not path_param == 'results':
            return self._ok(provider.to_json())

        provider_results = provider.cache.get_results(show_slug=show_slug, season=season, episode=episode)

        arg_page = self._get_page()
        arg_limit = self._get_limit(default=50)

        def data_generator():
            """Read log lines based on the specified criteria."""
            start = arg_limit * (arg_page - 1) + 1

            for item in provider_results[start - 1:start - 1 + arg_limit]:
                episodes = [int(ep) for ep in item['episodes'].strip('|').split('|') if ep != '']
                yield {
                    'identifier': item['identifier'],
                    'release': item['name'],
                    'season': item['season'],
                    'episodes': episodes,
                    # For now if episodes is 0 or (multiepisode) mark as season pack.
                    'seasonPack': len(episodes) == 0 or len(episodes) > 1,
                    'indexer': item['indexer'],
                    'seriesId': item['indexerid'],
                    'showSlug': show_slug,
                    'url': item['url'],
                    'time': datetime.fromtimestamp(item['time']),
                    'quality': item['quality'],
                    'releaseGroup': item['release_group'],
                    'dateAdded': datetime.fromtimestamp(item['date_added']),
                    'version': item['version'],
                    'seeders': item['seeders'],
                    'size': item['size'],
                    'leechers': item['leechers'],
                    'pubdate': parser.parse(item['pubdate']).replace(microsecond=0) if item['pubdate'] else None,
                    'provider': {
                        'id': provider.get_id(),
                        'name': provider.name,
                        'imageName': provider.image_name()
                    }
                }

        if not len(provider_results):
            return self._not_found('Provider cache results not found')

        return self._paginate(data_generator=data_generator)
