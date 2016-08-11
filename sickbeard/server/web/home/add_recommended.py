# coding=utf-8
#
# URL: https://sickrage.github.io
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.home.handler import Home
from tornado.routes import route


@route('/addRecommended(/?.*)')
class HomeAddRecommended(Home):
    """Landing page for the recommended shows."""

    def __init__(self, *args, **kwargs):
        """Initialize route."""
        super(HomeAddRecommended, self).__init__(*args, **kwargs)

    def index(self):
        """"Render template for route /home/addRecommeded."""
        t = PageTemplate(rh=self, filename="addRecommended.mako")
        return t.render(title='Add Recommended Shows', header='Add Recommended Shows',
                        topmenu='home', controller="addShows", action="index")
