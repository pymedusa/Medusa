# coding=utf-8

"""
NZB Client API for SABnzbd.

https://sabnzbd.org/
https://github.com/sabnzbd/sabnzbd
"""

from __future__ import unicode_literals

import datetime
import json
import logging

from medusa import app
from medusa.helper.common import sanitize_filename
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSafeSession

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

session = MedusaSafeSession()


def send_nzb(nzb):
    """
    Dispatch method for sending an nzb to sabnzbd using it's api.

    :param nzb: nzb SearchResult object
    :return: result of the communication with sabnzbd (True/False)
    """
    session.params.update({
        'output': 'json',
        'ma_username': app.SAB_USERNAME,
        'ma_password': app.SAB_PASSWORD,
        'apikey': app.SAB_APIKEY,
    })

    category = app.SAB_CATEGORY
    if nzb.series.is_anime:
        category = app.SAB_CATEGORY_ANIME

    # if it aired more than 7 days ago, override with the backlog category IDs
    for cur_ep in nzb.episodes:
        if datetime.date.today() - cur_ep.airdate > datetime.timedelta(days=7):
            category = app.SAB_CATEGORY_ANIME_BACKLOG if nzb.series.is_anime else app.SAB_CATEGORY_BACKLOG

    # set up a dict with the URL params in it
    params = {
        'cat': category,
    }

    if nzb.priority:
        params['priority'] = 2 if app.SAB_FORCED else 1

    if nzb.result_type == 'nzbdata' and nzb.extra_info:
        return send_nzb_post(params, nzb)
    else:
        return send_nzb_get(params, nzb)


def send_nzb_get(params, nzb):
    """
    Sends an NZB to SABnzbd via the API using a get request.

    :param nzb: The NZBSearchResult object to send to SAB
    :return: result of the communication with sabnzbd (True/False)
    """

    log.info('Sending NZB to SABnzbd')

    params.update({'name': nzb.url, 'mode': 'addurl'})
    url = urljoin(app.SAB_HOST, 'api')

    data = session.get_json(url, params=params, verify=False)
    if not data:
        log.info('Error connecting to sab, no data returned')
    else:
        result, text = _check_sab_response(data)
        log.debug('Result text from SAB: {0}', text)
        del text
        return result


def send_nzb_post(params, nzb):
    """
    Sends an NZB to SABnzbd via the API.

    :param params: Prepared post parameters.
    :param nzb: The NZBSearchResult object to send to SAB
    :return: result of the communication with sabnzbd (True/False)
    """

    log.info('Sending NZB to SABnzbd using the post multipart/form data.')
    url = urljoin(app.SAB_HOST, 'api')
    params['mode'] = 'addfile'
    files = {
        'name': nzb.extra_info[0]
    }

    data = session.params
    data.update(params)
    data['nzbname'] = sanitize_filename(nzb.name)

    # Empty session.params, because else these are added to the url.
    session.params = {}

    data = session.get_json(url, method='POST', data=data, files=files, verify=False)
    if not data:
        log.info('Error connecting to sab, no data returned')
    else:
        result, text = _check_sab_response(data)
        log.debug('Result text from SAB: {0}', text)
        del text
        return result


def _check_sab_response(jdata):
    """
    Check response from SAB

    :param jdata: Response from requests api call
    :return: a list of (Boolean, string) which is True if SAB is not reporting an error
    """
    error = jdata.get('error')

    if error == 'API Key Required':
        log.warning("Sabnzbd's API key is missing")
    elif error == 'API Key Incorrect':
        log.warning("Sabnzbd's API key is incorrect")
    elif error:
        log.error('Sabnzbd encountered an error: {0}', error)

    return not error, error or json.dumps(jdata)


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
    data = session.get_json(url, params={'mode': 'auth'}, verify=False)
    if not data:
        log.info('Error connecting to sab, no data returned')
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

    data = session.get_json(url, params={'mode': 'queue'}, verify=False)
    if not data:
        log.info('Error connecting to sab, no data returned')
    else:
        # check the result and determine if it's good or not
        result, text = _check_sab_response(data)
        return result, 'success' if result else text
