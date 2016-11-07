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

"""Custom exceptions used or raised by tvmaze_api."""

__author__ = "p0psicles"
__version__ = "1.0"

__all__ = ["tvmaze_error", "tvmaze_userabort", "tvmaze_shownotfound", "tvmaze_showincomplete",
           "tvmaze_seasonnotfound", "tvmaze_episodenotfound", "tvmaze_attributenotfound"]


class tvmaze_exception(Exception):
    """Any exception generated by tvmaze_api
    """
    pass


class tvmaze_error(tvmaze_exception):
    """An error with thetvdb.com (Cannot connect, for example)
    """
    pass


class tvmaze_userabort(tvmaze_exception):
    """User aborted the interactive selection (via
    the q command, ^c etc)
    """
    pass


class tvmaze_shownotfound(tvmaze_exception):
    """Show cannot be found on thetvdb.com (non-existant show)
    """
    pass


class tvmaze_showincomplete(tvmaze_exception):
    """Show found but incomplete on thetvdb.com (incomplete show)
    """
    pass


class tvmaze_seasonnotfound(tvmaze_exception):
    """Season cannot be found on thetvdb.com
    """
    pass


class tvmaze_episodenotfound(tvmaze_exception):
    """Episode cannot be found on thetvdb.com
    """
    pass


class tvmaze_attributenotfound(tvmaze_exception):
    """Raised if an episode does not have the requested
    attribute (such as a episode name)
    """
    pass
