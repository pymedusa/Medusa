# coding=utf-8

"""
NZB Client API for SABnzbd.

https://sabnzbd.org/
https://github.com/sabnzbd/sabnzbd
"""

from __future__ import unicode_literals

import datetime
import logging

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

from medusa.session.core import MedusaSession
from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

session = MedusaSession()


def send_nzb(nzb):
    """
    Sends an NZB to SABnzbd via the API.

    :param nzb: The NZBSearchResult object to send to SAB
    """
    session.params.update({
        'output': 'json',
        'ma_username': app.SAB_USERNAME,
        'ma_password': app.SAB_PASSWORD,
        'apikey': app.SAB_APIKEY,
    })

    category = app.SAB_CATEGORY
    if nzb.show.is_anime:
        category = app.SAB_CATEGORY_ANIME

    # if it aired more than 7 days ago, override with the backlog category IDs
    for cur_ep in nzb.episodes:
        if datetime.date.today() - cur_ep.airdate > datetime.timedelta(days=7):
            category = app.SAB_CATEGORY_ANIME_BACKLOG if nzb.show.is_anime else app.SAB_CATEGORY_BACKLOG

    # set up a dict with the URL params in it
    params = {
        'cat': category,
        'mode': 'addurl',
        'name': nzb.url,
    }

    if nzb.priority:
        params['priority'] = 2 if app.SAB_FORCED else 1

    log.info('Sending NZB to SABnzbd')
    url = urljoin(app.SAB_HOST, 'api')

    response = session.get(url, params=params, verify=False)

    try:
        data = response.json()
    except ValueError:
        log.info('Error connecting to sab, no data returned')
    else:
        log.debug('Result text from SAB: {0}', data)
        result, text = _check_sab_response(data)
        del text
        return result


def _check_sab_response(jdata):
    """
    Check response from SAB

    :param jdata: Response from requests api call
    :return: a list of (Boolean, string) which is True if SAB is not reporting an error
    """
    error = jdata.get('error')

    if error == 'API Key Incorrect':
        log.warning("Sabnzbd's API key is incorrect")
    elif error:
        log.error('Sabnzbd encountered an error: {0}', error)

    return not error, error or jdata


def get_sab_access_method(host=None):
    """
    Find out how we should connect to SAB

    :param host: hostname where SAB lives
    :return: (boolean, string) with True if method was successful
    """
    session.params.update({
        'output': 'json',
        'ma_username': app.SAB_USERNAME,
        'ma_password': app.SAB_PASSWORD,
        'apikey': app.SAB_APIKEY,
    })
    url = urljoin(host, 'api')
    response = session.get(url, params={'mode': 'auth'}, verify=False)

    try:
        data = response.json()
    except ValueError:
        return False, response
    else:
        return _check_sab_response(data)


def test_authentication(host=None, username=None, password=None, apikey=None):
    """
    Sends a simple API request to SAB to determine if the given connection information is connect

    :param host: The host where SAB is running (incl port)
    :param username: The username to use for the HTTP request
    :param password: The password to use for the HTTP request
    :param apikey: The API key to provide to SAB
    :return: A tuple containing the success boolean and a message
    """
    session.params.update({
        'ma_username': username,
        'ma_password': password,
        'apikey': apikey,
    })
    url = urljoin(host, 'api')

    response = session.get(url, params={'mode': 'queue'}, verify=False)
    try:
        data = response.json()
    except ValueError:
        return False, response
    else:
        # check the result and determine if it's good or not
        result, sab_text = _check_sab_response(data)
        return result, 'success' if result else sab_text
