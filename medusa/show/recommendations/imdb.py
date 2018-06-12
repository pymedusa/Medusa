# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import posixpath
import re
from builtins import object

from imdbpie import imdbpie

from medusa import helpers
from medusa.cache import recommended_show_cache
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession
from medusa.show.recommendations.recommended import (
    RecommendedShow, cached_get_imdb_show_details, create_key_from_show,
    update_recommended_show_cache_index
)

from requests import RequestException

from six import binary_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

imdb_api = imdbpie.Imdb()


class ImdbPopular(object):
    """Gets a list of most popular TV show from imdb."""

    def __init__(self):
        """Initialize class."""
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = MedusaSession()
        self.recommender = 'IMDB Popular'
        self.default_img_src = 'poster.png'

    @recommended_show_cache.cache_on_arguments(namespace='imdb', function_key_generator=create_key_from_show)
    def _create_recommended_show(self, show, storage_key=None):
        """Create the RecommendedShow object from the returned showobj."""
        tvdb_id = helpers.get_tvdb_from_id(show.get('imdb_tt'), 'IMDB')

        if not tvdb_id:
            return None

        rec_show = RecommendedShow(
            self,
            show.get('imdb_tt'),
            show.get('name'),
            INDEXER_TVDBV2,
            int(tvdb_id),
            **{'rating': show.get('rating'),
               'votes': show.get('votes'),
               'image_href': show.get('imdb_url')}
        )

        if show.get('image_url'):
            rec_show.cache_image(show.get('image_url'))

        return rec_show

    def fetch_popular_shows(self):
        """Get popular show information from IMDB."""
        popular_shows = []

        imdb_result = imdb_api.get_popular_shows()

        for imdb_show in imdb_result['ranks']:
            show = {}
            imdb_id = show['imdb_tt'] = imdb_show['id'].strip('/').split('/')[-1]

            if imdb_id:
                show_details = cached_get_imdb_show_details(imdb_id)
                if show_details:
                    try:
                        show['year'] = imdb_show.get('year')
                        show['name'] = imdb_show['title']
                        show['image_url_large'] = imdb_show['image']['url']
                        show['image_path'] = posixpath.join('images', 'imdb_popular',
                                                              os.path.basename(show['image_url_large']))
                        show['image_url'] = '{0}{1}'.format(imdb_show['image']['url'].split('V1')[0], '_SY600_AL_.jpg')
                        show['imdb_url'] = 'http://www.imdb.com{imdb_id}'.format(imdb_id=imdb_show['id'])
                        show['votes'] = show_details['ratings'].get('ratingCount', 0)
                        show['outline'] = show_details['plot'].get('outline', {}).get('text')
                        show['rating'] = show_details['ratings'].get('rating', 0)
                    except Exception as error:
                        log.warning('Could not parse show {imdb_id} with error: {error!r}',
                                    {'imdb_id': imdb_id, 'error': error})
                else:
                    continue

            if all([show['year'], show['name'], show['imdb_tt']]):
                popular_shows.append(show)

        result = []
        for show in popular_shows:
            try:
                recommended_show = self._create_recommended_show(show, storage_key=b'imdb_{0}'.format(show['imdb_tt']))
                if recommended_show:
                    result.append(recommended_show)
            except RequestException:
                log.warning(
                    u'Could not connect to indexers to check if you already have'
                    u' this show in your library: {show} ({year})',
                    {'show': show['name'], 'year': show['name']}
                )

        # Update the dogpile index. This will allow us to retrieve all stored dogpile shows from the dbm.
        update_recommended_show_cache_index('imdb', [binary_type(s.show_id) for s in result])

        return result

    @staticmethod
    def change_size(image_url, factor=3):
        """Change the size of the image we get from IMDB.

        :param: image_url: Image source URL
        :param: factor: Multiplier for the image size
        """
        match = re.search(r'(.+[X|Y])(\d+)(_CR\d+,\d+,)(\d+),(\d+)', image_url)

        if match:
            matches = list(match.groups())
            matches[1] = int(matches[1]) * factor
            matches[3] = int(matches[3]) * factor
            matches[4] = int(matches[4]) * factor

            return '{0}{1}{2}{3},{4}_AL_.jpg'.format(matches[0], matches[1], matches[2],
                                                     matches[3], matches[4])
        else:
            return image_url
