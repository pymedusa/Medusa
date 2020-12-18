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
from __future__ import unicode_literals

import datetime
import re

from dateutil import tz

from medusa import db, logger
from medusa.app import app
from medusa.helper.common import try_int
from medusa.session.core import MedusaSafeSession

from six import iteritems

try:
    app_timezone = tz.tzwinlocal() if tz.tzwinlocal else tz.tzlocal()
except Exception:
    app_timezone = tz.tzlocal()

# regex to parse time (12/24 hour format)
time_regex = re.compile(r'(?P<hour>\d{1,2})(?:[:.](?P<minute>\d{2})?)? ?(?P<meridiem>[PA]\.? ?M?)?\b', re.I)

network_dict = None
missing_network_timezones = set()

session = MedusaSafeSession()


# update the network timezone table
def update_network_dict():
    """Update timezone information from Medusa repositories."""
    logger.log('Started updating network timezones', logger.DEBUG)
    url = '{base_url}/sb_network_timezones/network_timezones.txt'.format(base_url=app.BASE_PYMEDUSA_URL)
    response = session.get(url)
    if not response or not response.text:
        logger.log('Updating network timezones failed, this can happen from time to time. URL: %s' % url, logger.INFO)
        load_network_dict()
        return

    remote_networks = {}
    try:
        for line in response.text.splitlines():
            (key, val) = line.rsplit(':', 1)
            if key is None or val is None:
                continue
            remote_networks[key] = val
    except (IOError, OSError) as error:
        logger.log('Unable to build the network dictionary. Aborting update. Error: {error}'.format
                   (error=error), logger.WARNING)
        return

    # Don't continue because if empty dict, var `existing` be false for all networks, thus deleting all
    if not remote_networks:
        logger.log('Unable to update network timezones as fetched network dict is empty', logger.WARNING)
        return

    cache_db_con = db.DBConnection('cache.db')
    sql_result = cache_db_con.select('SELECT network_name, timezone FROM network_timezones;')

    network_list = {
        row['network_name']: row['timezone']
        for row in sql_result
    }

    queries = []
    for network, timezone in iteritems(remote_networks):
        existing = network in network_list
        if not existing:
            queries.append(['INSERT OR IGNORE INTO network_timezones VALUES (?,?);', [network, timezone]])
        elif network_list[network] != timezone:
            queries.append(['UPDATE OR IGNORE network_timezones SET timezone = ? WHERE network_name = ?;', [timezone, network]])

        if existing:
            # if the network from cache DB is in the remote network, remove from the `to remove` list
            del network_list[network]

    if network_list:
        # Delete all networks that are not in the remote network list
        purged = [x for x in network_list]
        queries.append(['DELETE FROM network_timezones WHERE network_name IN (%s);' % ','.join(['?'] * len(purged)), purged])

    if queries:
        cache_db_con.mass_action(queries)
        load_network_dict()

    logger.log('Finished updating network timezones', logger.DEBUG)


# load network timezones from db into dict
def load_network_dict():
    """Load network timezones from db into dict network_dict (global dict)."""
    try:
        cache_db_con = db.DBConnection('cache.db')
        sql_result = cache_db_con.select('SELECT network_name, timezone FROM network_timezones;')
        if not sql_result:
            update_network_dict()
            sql_result = cache_db_con.select('SELECT network_name, timezone FROM network_timezones;')

        d = {
            row['network_name']: row['timezone']
            for row in sql_result
        }

    except Exception:
        d = {}
    # pylint: disable=global-statement
    global network_dict
    network_dict = d


# get timezone of a network or return default timezone
def get_network_timezone(network, _network_dict):
    """
    Get a timezone of a network from a given network dict.

    :param network: network to look up (needle)
    :param _network_dict: dict to look up in (haystack)
    :return:
    """
    # Get the name of the networks timezone from _network_dict
    network_tz_name = _network_dict[network] if network in _network_dict else None

    if not network_tz_name and network and network not in missing_network_timezones:
        missing_network_timezones.add(network)
        if network is not None:
            logger.log('Missing time zone for network: %s' % network, logger.ERROR)

    return tz.gettz(network_tz_name) if network_tz_name else app_timezone


# parse date and time string into local time
def parse_date_time(d, t, network):
    """
    Parse date and time string into local time.

    :param d: date string
    :param t: time string
    :param network: network to use as base
    :return: datetime object containing local time
    """
    if not network_dict:
        load_network_dict()

    parsed_time = time_regex.search(t)
    network_tz = get_network_timezone(network, network_dict)

    hr = 0
    m = 0

    if parsed_time:
        hr = try_int(parsed_time.group('hour'))
        m = try_int(parsed_time.group('minute'))

        ap = parsed_time.group('meridiem')
        ap = ap[0].lower() if ap else ''

        if ap == 'a' and hr == 12:
            hr -= 12
        elif ap == 'p' and hr != 12:
            hr += 12

        hr = hr if 0 <= hr <= 23 else 0
        m = m if 0 <= m <= 59 else 0

    result = datetime.datetime.fromordinal(max(try_int(d), 1))

    return result.replace(hour=hr, minute=m, tzinfo=network_tz)


def test_timeformat(time_string):
    return time_regex.search(time_string) is not None
