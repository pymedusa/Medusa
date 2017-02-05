# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>

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

from requests.compat import urljoin
from . import app, helpers, logger

session = helpers.make_session()


def sendNZB(nzb):  # pylint:disable=too-many-return-statements, too-many-branches, too-many-statements
    """
    Sends an NZB to SABnzbd via the API.

    :param nzb: The NZBSearchResult object to send to SAB
    """

    category = app.SAB_CATEGORY
    if nzb.show.is_anime:
        category = app.SAB_CATEGORY_ANIME

    # if it aired more than 7 days ago, override with the backlog category IDs
    for cur_ep in nzb.episodes:
        if datetime.date.today() - cur_ep.airdate > datetime.timedelta(days=7):
            category = app.SAB_CATEGORY_ANIME_BACKLOG if nzb.show.is_anime else app.SAB_CATEGORY_BACKLOG

    # set up a dict with the URL params in it
    params = {'output': 'json'}
    if app.SAB_USERNAME:
        params['ma_username'] = app.SAB_USERNAME
    if app.SAB_PASSWORD:
        params['ma_password'] = app.SAB_PASSWORD
    if app.SAB_APIKEY:
        params['apikey'] = app.SAB_APIKEY

    if category:
        params['cat'] = category

    if nzb.priority:
        params['priority'] = 2 if app.SAB_FORCED else 1

    logger.log('Sending NZB to SABnzbd')
    url = urljoin(app.SAB_HOST, 'api')

    if nzb.resultType == 'nzb':
        params['mode'] = 'addurl'
        params['name'] = nzb.url
        jdata = helpers.get_url(url, params=params, session=session, returns='json', verify=False)
    elif nzb.resultType == 'nzbdata':
        params['mode'] = 'addfile'
        multiPartParams = {'nzbfile': (nzb.name + '.nzb', nzb.extraInfo[0])}
        jdata = helpers.get_url(url, params=params, file=multiPartParams, session=session, returns='json', verify=False)

    if not jdata:
        logger.log('Error connecting to sab, no data returned')
        return False

    logger.log('Result text from SAB: {0}'.format(jdata), logger.DEBUG)

    result, _ = _checkSabResponse(jdata)
    return result


def _checkSabResponse(jdata):
    """
    Check response from SAB

    :param jdata: Response from requests api call
    :return: a list of (Boolean, string) which is True if SAB is not reporting an error
    """
    if 'error' in jdata:
        if jdata['error'] == 'API Key Incorrect':
            logger.log("Sabnzbd's API key is incorrect", logger.WARNING)
        else:
            logger.log('Sabnzbd encountered an error: {0}'.format(jdata['error']), logger.ERROR)
        return False, jdata['error']
    else:
        return True, jdata


def getSabAccesMethod(host=None):
    """
    Find out how we should connect to SAB

    :param host: hostname where SAB lives
    :return: (boolean, string) with True if method was successful
    """
    params = {'mode': 'auth', 'output': 'json'}
    url = urljoin(host, 'api')
    data = helpers.get_url(url, params=params, session=session, returns='json', verify=False)
    if not data:
        return False, data

    return _checkSabResponse(data)


def testAuthentication(host=None, username=None, password=None, apikey=None):
    """
    Sends a simple API request to SAB to determine if the given connection information is connect

    :param host: The host where SAB is running (incl port)
    :param username: The username to use for the HTTP request
    :param password: The password to use for the HTTP request
    :param apikey: The API key to provide to SAB
    :return: A tuple containing the success boolean and a message
    """

    # build up the URL parameters
    params = {
        'mode': 'queue',
        'output': 'json',
        'ma_username': username,
        'ma_password': password,
        'apikey': apikey
    }

    url = urljoin(host, 'api')

    data = helpers.get_url(url, params=params, session=session, returns='json', verify=False)
    if not data:
        return False, data

    # check the result and determine if it's good or not
    result, sabText = _checkSabResponse(data)
    if not result:
        return False, sabText

    return True, 'Success'
