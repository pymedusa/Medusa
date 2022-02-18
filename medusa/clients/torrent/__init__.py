# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
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
"""Clients module."""
from __future__ import unicode_literals


_clients = [
    'deluge',
    'deluged',
    'downloadstation',
    'mlnet',
    'qbittorrent',
    'rtorrent',
    'transmission',
    'utorrent',
]


def get_client_module(name):
    """Import the client module for the given name."""
    return __import__('{prefix}.{name}'.format(prefix=__name__, name=name.lower()), fromlist=_clients)


def get_client_class(name):
    """Return the client API class for the given name.

    :param name:
    :type name: string
    :return:
    :rtype: class
    """
    return get_client_module(name).api
