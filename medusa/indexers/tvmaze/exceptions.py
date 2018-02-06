# coding=utf-8
# Author: p0psicles
#
# This file is part of Medusa.
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

"""Custom exceptions used or raised by tvdb_api."""

__author__ = "p0psicles"
__version__ = "1.0"

__all__ = ["tvdb_error", "tvdb_userabort", "tvdb_shownotfound", "tvdb_showincomplete",
           "tvdb_seasonnotfound", "tvdb_episodenotfound", "tvdb_attributenotfound"]


class tvdb_exception(Exception):
    """Any exception generated by tvdb_api
    """
    pass


class tvdb_error(tvdb_exception):
    """An error with thetvdb.com (Cannot connect, for example)
    """
    pass


class tvdb_userabort(tvdb_exception):
    """User aborted the interactive selection (via
    the q command, ^c etc)
    """
    pass


class tvdb_shownotfound(tvdb_exception):
    """Show cannot be found on thetvdb.com (non-existant show)
    """
    pass


class tvdb_showincomplete(tvdb_exception):
    """Show found but incomplete on thetvdb.com (incomplete show)
    """
    pass


class tvdb_seasonnotfound(tvdb_exception):
    """Season cannot be found on thetvdb.com
    """
    pass


class tvdb_episodenotfound(tvdb_exception):
    """Episode cannot be found on thetvdb.com
    """
    pass


class tvdb_attributenotfound(tvdb_exception):
    """Raised if an episode does not have the requested
    attribute (such as a episode name)
    """
    pass
