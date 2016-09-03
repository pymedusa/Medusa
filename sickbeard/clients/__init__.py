# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
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
"""Clients module."""

from __future__ import unicode_literals


_clients = [
    'deluge',
    'deluged',
    'download_station',
    'mlnet',
    'qbittorrent',
    'rtorrent',
    'transmission',
    'utorrent',
]


def get_client_module(name):
    """Import the client module for the given name."""
    return __import__('{prefix}.{name}_client'.format(prefix=__name__, name=name.lower()), fromlist=_clients)


def get_client_class(name):
    """Return the client API class for the given name.

    :param name:
    :type name: string
    :return:
    :rtype: class
    """
    return get_client_module(name).api
