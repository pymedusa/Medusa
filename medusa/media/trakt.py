# coding=utf-8
# This file is part of Medusa.
#

#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

import os
import time
from shutil import copyfile

from medusa.helpers import (download_file, make_session)
from .generic import GenericMedia
from .. import app
from ..helper.common import try_int
from tvdbapiv2 import (ApiClient, AuthenticationApi, SeriesApi)
from ..image_cache import ImageCache

def get_tvdbv2_api():
    """Initiate the tvdb api v2."""
    api_base_url = 'https://api.thetvdb.com'

    # client_id = 'username'  # (optional! Only required for the /user routes)
    # client_secret = 'pass'  # (optional! Only required for the /user routes)
    apikey = '0629B785CE550C8D'

    authentication_string = {'apikey': apikey, 'username': '', 'userpass': ''}
    unauthenticated_client = ApiClient(api_base_url)
    auth_api = AuthenticationApi(unauthenticated_client)
    access_token = auth_api.login_post(authentication_string)
    auth_client = ApiClient(api_base_url, 'Authorization', 'Bearer ' + access_token.token)
    series_api = SeriesApi(auth_client)

    return series_api

class ShowTrakt(GenericMedia):
    """Get the poster of a show."""

    def __init__(self, indexer_id, media_format='normal'):
        """Initialize Class"""
        self.indexer_id = try_int(indexer_id, 0)

        if media_format in ('normal', 'thumb'):
            self.media_format = media_format
        else:
            self.media_format = 'normal'
        self.tvdb_api_v2 = get_tvdbv2_api()
        self.session = make_session()

    def get_default_media_name(self):
        """Default Image"""
        return 'trakt-default.png'

    def get_media_path(self):
        """Media Path"""
        if self.media_format == 'normal':
            if ImageCache().has_trakt(self.indexer_id):
                return ImageCache().trakt_path(self.indexer_id)
            else:
                path = os.path.abspath(os.path.join(app.CACHE_DIR, 'images', 'trakt'))
                image_path = os.path.join(self.get_media_root(), 'images', self.get_default_media_name())
                if not os.path.exists(path):
                    os.makedirs(path)

                if ImageCache().has_trakt_dummy(self.indexer_id):
                    one_month_old = time.time() - 2592000
                    if os.path.getmtime(ImageCache().trakt_dummy_path(self.indexer_id)) < one_month_old:
                        os.unlink(ImageCache().trakt_dummy_path(self.indexer_id))
                    else:
                        return ImageCache().trakt_dummy_path(self.indexer_id)

                try:
                    image = self.tvdb_api_v2.series_id_images_query_get(self.indexer_id, key_type='poster_thumb').data[0].file_name
                    download_file('http://thetvdb.com/banners/{0}'.format(image), ImageCache().trakt_path(self.indexer_id), session=self.session)
                except Exception:
                    copyfile(image_path, ImageCache().trakt_dummy_path(self.indexer_id))
                    return ImageCache().trakt_dummy_path(self.indexer_id)

                return ImageCache().trakt_path(self.indexer_id)
        return ''

    def get_static_media_path(self):
        """
        :return: The full path to the media
        """
        media_path = self.get_media_path()

        if os.path.isfile(media_path):
            return os.path.normpath(media_path)

        image_path = os.path.join(self.get_media_root(), 'images', self.get_default_media_name())

        return image_path.replace('\\', '/')
