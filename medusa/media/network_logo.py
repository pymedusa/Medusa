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

from __future__ import unicode_literals

from os.path import join

from medusa.media.generic import GenericMedia


class ShowNetworkLogo(GenericMedia):
    """Get the network logo of a show."""

    @property
    def default_media_name(self):
        """Get default icon for Network missing a logo."""
        return join('network', 'nonetwork.png')

    @property
    def media_path(self):
        """Get the relative path to the media."""
        series = self.series
        if series:
            return join(self.get_media_root(), 'img', 'network', series.network_logo_name + '.png')
        else:
            return ''
