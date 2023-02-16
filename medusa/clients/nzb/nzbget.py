# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
import socket
from base64 import standard_b64encode
from contextlib import suppress
from urllib.parse import quote
from xmlrpc.client import Error, ProtocolError, ServerProxy

from medusa import app
from medusa.common import Quality
from medusa.helper.common import try_int
from medusa.helper.exceptions import DownloadClientConnectionException
from medusa.logger.adapters.style import BraceAdapter

import ttl_cache

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def nzb_connection(url):
    """
    Connect to NZBget client.

    :param url: nzb url to connect
    :return: True if connected, else False
    """
    nzb_get_rpc = ServerProxy(url)
    try:
        if nzb_get_rpc.writelog('INFO', 'Medusa connected to test connection.'):
            msg = 'Successfully connected to NZBget'
            log.debug(msg)
        else:
            msg = 'Successfully connected to NZBget but unable to send a message'
            log.warning(msg)

        return True, msg

    except ProtocolError as error:
        if error.errmsg == 'Unauthorized':
            msg = 'NZBget username or password is incorrect.'
            log.warning(msg)
        else:
            msg = f'Protocol Error: {error.errmsg}'
            log.error(msg)

        return False, msg

    except Error as error:
        msg = ('Please check your NZBget host and port (if it is running).'
               ' NZBget is not responding to this combination.'
               f' Error: {error}')
        log.warning(msg)

        return False, msg

    except socket.error as error:
        msg = ('Please check your NZBget host and port (if it is running).'
               ' NZBget is not responding to this combination.'
               f' Socket Error: {error}')
        log.warning(msg)

        return False, msg


def test_authentication(host=None, username=None, password=None, use_https=False):
    """
    Test NZBget client connection.

    :param host: nzb host to connect
    :param username: nzb username
    :param password: nzb password
    :param use_https: If we should use https or not

    :return  True if connected. Else False
    """
    url = 'http{}://{}:{}@{}/xmlrpc'.format(
        's' if use_https or app.NZBGET_USE_HTTPS else '',
        quote(username or app.NZBGET_USERNAME, safe=''),
        quote(password or app.NZBGET_PASSWORD, safe=''),
        quote(host or app.NZBGET_HOST, safe='/:')
    )

    return nzb_connection(url)


def send_nzb(nzb, proper=False):
    """
    Send NZB to NZBGet client.

    :param nzb: nzb object
    :param proper: True if a Proper download, False if not.
    """
    if app.NZBGET_HOST is None:
        log.warning('No NZBget host found in configuration.'
                    ' Please configure it.')
        return False

    nzb_get_prio = 0
    category = app.NZBGET_CATEGORY
    if nzb.series.is_anime:
        category = app.NZBGET_CATEGORY_ANIME

    url = 'http{}://{}:{}@{}/xmlrpc'.format(
        's' if app.NZBGET_USE_HTTPS else '',
        quote(app.NZBGET_USERNAME, safe=''),
        quote(app.NZBGET_PASSWORD, safe=''),
        quote(app.NZBGET_HOST, safe='/:')
    )

    if not nzb_connection(url):
        return False

    nzb_get_rpc = ServerProxy(url)

    dupekey = ''
    dupescore = 0
    # if it aired recently make it high priority and generate DupeKey/Score
    for cur_ep in nzb.episodes:
        if dupekey == '':
            dupekey = 'medusa-{slug}'.format(slug=cur_ep.series.identifier.slug)
        dupekey += '-' + '{0}.{1}'.format(cur_ep.season, cur_ep.episode)
        if datetime.date.today() - cur_ep.airdate <= datetime.timedelta(days=7):
            nzb_get_prio = app.NZBGET_PRIORITY
        else:
            category = app.NZBGET_CATEGORY_BACKLOG
            if nzb.series.is_anime:
                category = app.NZBGET_CATEGORY_ANIME_BACKLOG

    if nzb.quality != Quality.UNKNOWN:
        dupescore = nzb.quality * 100
    if proper:
        dupescore += 10

    nzb_content_64 = None
    if nzb.result_type == 'nzbdata':
        data = nzb.extra_info[0]
        nzb_content_64 = standard_b64encode(data).decode()

    log.info('Sending NZB to NZBget')
    log.debug('URL: {}', url)

    try:
        # Version < 12 not supported.
        nzbget_version_str = nzb_get_rpc.version()
        nzbget_version = try_int(
            nzbget_version_str[:nzbget_version_str.find('.')]
        )

        if nzbget_version == 12:
            if nzb_content_64 is not None:
                nzbget_result = nzb_get_rpc.append(
                    nzb.name + '.nzb', category, nzb_get_prio, False,
                    nzb_content_64, False, dupekey, dupescore, 'score'
                )
            else:
                nzbget_result = nzb_get_rpc.appendurl(
                    nzb.name + '.nzb', category, nzb_get_prio, False, nzb.url,
                    False, dupekey, dupescore, 'score'
                )

        # v13+ has a new combined append method that accepts both (url and
        # content) also the return value has changed from boolean to integer
        # (Positive number representing NZBID of the queue item. 0 and negative
        # numbers represent error codes.)
        elif nzbget_version >= 13:
            nzbget_result = nzb_get_rpc.append(
                nzb.name + '.nzb',
                nzb_content_64 if nzb_content_64 is not None else nzb.url,
                category, nzb_get_prio, False, False, dupekey, dupescore,
                'score'
            )
        else:
            if nzb_content_64 is not None:
                nzbget_result = nzb_get_rpc.append(
                    nzb.name + '.nzb', category, nzb_get_prio, False,
                    nzb_content_64
                )
            else:
                nzbget_result = nzb_get_rpc.appendurl(
                    nzb.name + '.nzb', category, nzb_get_prio, False, nzb.url
                )

        if nzbget_result:
            log.debug('NZB sent to NZBget successfully, queued with NZBID {nzbid}', {'nzbid': nzbget_result})
            return nzbget_result
        else:
            log.warning('NZBget could not add {name}.nzb to the queue',
                        {'name': nzb.name})
            return nzbget_result
    except Exception:
        log.warning('Connect Error to NZBget: could not add {name}.nzb to the'
                    ' queue', {'name': nzb.name})
        return -1


@ttl_cache(60.0)
def _get_nzb_queue():
    """Return a list of all groups (nzbs) currently being donloaded or postprocessed."""
    url = 'http{}://{}:{}@{}/xmlrpc'.format(
        's' if app.NZBGET_USE_HTTPS else '',
        quote(app.NZBGET_USERNAME, safe=''),
        quote(app.NZBGET_PASSWORD, safe=''),
        quote(app.NZBGET_HOST, safe='/:')
    )

    if not nzb_connection(url):
        raise DownloadClientConnectionException('Error while fetching nzbget queue')

    nzb_get_rpc = ServerProxy(url)
    try:
        nzb_groups = nzb_get_rpc.listgroups()
    except ConnectionRefusedError as error:
        raise DownloadClientConnectionException(f'Error while fetching nzbget history. Error: {error}')

    return nzb_groups


@ttl_cache(60.0)
def _get_nzb_history():
    """Return a list of all groups (nzbs) from history."""
    url = 'http{}://{}:{}@{}/xmlrpc'.format(
        's' if app.NZBGET_USE_HTTPS else '',
        quote(app.NZBGET_USERNAME, safe=''),
        quote(app.NZBGET_PASSWORD, safe=''),
        quote(app.NZBGET_HOST, safe='/:')
    )

    if not nzb_connection(url):
        raise DownloadClientConnectionException('Error while fetching nzbget history')

    nzb_get_rpc = ServerProxy(url)
    try:
        nzb_groups = nzb_get_rpc.history()
    except ConnectionRefusedError as error:
        raise DownloadClientConnectionException(f'Error while fetching nzbget history. Error: {error}')

    return nzb_groups


def get_nzb_by_id(nzb_id):
    """Look in download queue and history for a specific nzb."""
    nzb_active = _get_nzb_queue()
    for nzb in nzb_active or []:
        with suppress(ValueError):
            if nzb['NZBID'] == int(nzb_id):
                return nzb

    nzb_history = _get_nzb_history()
    for nzb in nzb_history or []:
        with suppress(ValueError):
            if nzb['NZBID'] == int(nzb_id):
                return nzb


def nzb_completed(nzo_id):
    """Check if an nzb has completed download."""
    nzb = get_status(nzo_id)
    if not nzb:
        return False

    return str(nzb) == 'Completed'


def get_status(nzo_id):
    """
    Return nzb status (Paused, Downloading, Downloaded, Failed, Extracting).

    :return: ClientStatus object.
    """
    from medusa.schedulers.download_handler import ClientStatus

    nzb = get_nzb_by_id(nzo_id)
    status = None
    if not nzb:
        return False

    client_status = ClientStatus()
    # Map status to a standard ClientStatus.
    if '/' in nzb['Status']:
        status, _ = nzb['Status'].split('/')
    else:
        status = nzb['Status']

    # Queue status checks (Queued is not recorded as status)
    if status == 'DOWNLOADING':
        client_status.set_status_string('Downloading')

    if status == 'PAUSED':
        client_status.set_status_string('Paused')

    if status == 'UNPACKING':
        client_status.set_status_string('Extracting')

    # History status checks.
    if status == 'DELETED':  # Mostly because of duplicate checks.
        client_status.set_status_string('Aborted')

    if status == 'SUCCESS':
        client_status.set_status_string('Completed')

    if status == 'FAILURE':
        client_status.set_status_string('Failed')

    # Get Progress
    if status == 'SUCCESS':
        client_status.progress = 100
    elif nzb.get('percentage'):
        client_status.progress = int(nzb['percentage'])

    client_status.destination = nzb.get('DestDir', '')

    client_status.resource = nzb.get('NZBFilename')

    return client_status
