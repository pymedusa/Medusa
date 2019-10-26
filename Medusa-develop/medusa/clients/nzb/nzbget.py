# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
import socket
from base64 import standard_b64encode
from xmlrpc.client import Error, ProtocolError, ServerProxy

from medusa import app
from medusa.common import Quality
from medusa.helper.common import try_int
from medusa.logger.adapters.style import BraceAdapter

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def NZBConnection(url):
    """Method to connect to NZBget client.

    :param url: nzb url to connect
    :return: True if connected, else False
    """
    nzbGetRPC = ServerProxy(url)
    try:
        if nzbGetRPC.writelog('INFO', 'Medusa connected to test connection.'):
            log.debug('Successfully connected to NZBget')
        else:
            log.warning('Successfully connected to NZBget but unable to'
                        ' send a message')
        return True

    except ProtocolError as error:
        if error.errmsg == 'Unauthorized':
            log.warning('NZBget username or password is incorrect.')
        else:
            log.error('Protocol Error: {msg}', {'msg': error.errmsg})
        return False

    except Error as error:
        log.warning('Please check your NZBget host and port (if it is running).'
                    ' NZBget is not responding to this combination.'
                    ' Error: {msg}', {'msg': error.errmsg})
        return False

    except socket.error as error:
        log.warning('Please check your NZBget host and port (if it is running).'
                    ' NZBget is not responding to this combination.'
                    ' Socket Error: {msg}', {'msg': error})
        return False


def testNZB(host, username, password, use_https):
    """Test NZBget client connection.

    :param host: nzb host to connect
    :param username: nzb username
    :param password: nzb password
    :param use_https: If we should use https or not

    :return  True if connected. Else False
    """
    url = 'http{}://{}:{}@{}/xmlrpc'.format(
        's' if use_https else '',
        username,
        password,
        host)
    return NZBConnection(url)


def sendNZB(nzb, proper=False):
    """
    Sends NZB to NZBGet client

    :param nzb: nzb object
    :param proper: True if a Proper download, False if not.
    """
    if app.NZBGET_HOST is None:
        log.warning('No NZBget host found in configuration.'
                    ' Please configure it.')
        return False

    addToTop = False
    nzbgetprio = 0
    category = app.NZBGET_CATEGORY
    if nzb.series.is_anime:
        category = app.NZBGET_CATEGORY_ANIME

    url = 'http{}://{}:{}@{}/xmlrpc'.format(
        's' if app.NZBGET_USE_HTTPS else '',
        app.NZBGET_USERNAME,
        app.NZBGET_PASSWORD,
        app.NZBGET_HOST)

    if not NZBConnection(url):
        return False

    nzbGetRPC = ServerProxy(url)

    dupekey = ''
    dupescore = 0
    # if it aired recently make it high priority and generate DupeKey/Score
    for cur_ep in nzb.episodes:
        if dupekey == '':
            if cur_ep.series.indexer == 1:
                dupekey = 'Medusa-' + text_type(cur_ep.series.indexerid)
            elif cur_ep.series.indexer == 2:
                dupekey = 'Medusa-tvr' + text_type(cur_ep.series.indexerid)
        dupekey += '-' + text_type(cur_ep.season) + '.' + text_type(cur_ep.episode)
        if datetime.date.today() - cur_ep.airdate <= datetime.timedelta(days=7):
            addToTop = True
            nzbgetprio = app.NZBGET_PRIORITY
        else:
            category = app.NZBGET_CATEGORY_BACKLOG
            if nzb.series.is_anime:
                category = app.NZBGET_CATEGORY_ANIME_BACKLOG

    if nzb.quality != Quality.UNKNOWN:
        dupescore = nzb.quality * 100
    if proper:
        dupescore += 10

    nzbcontent64 = None
    if nzb.result_type == 'nzbdata':
        data = nzb.extra_info[0]
        nzbcontent64 = standard_b64encode(data).decode()

    log.info('Sending NZB to NZBget')
    log.debug('URL: {}', url)

    try:
        # Find out if nzbget supports priority (Version 9.0+),
        # old versions beginning with a 0.x will use the old command
        nzbget_version_str = nzbGetRPC.version()
        nzbget_version = try_int(
            nzbget_version_str[:nzbget_version_str.find('.')]
        )
        if nzbget_version == 0:
            if nzbcontent64:
                nzbget_result = nzbGetRPC.append(
                    nzb.name + '.nzb',
                    category,
                    addToTop,
                    nzbcontent64
                )
            else:
                if nzb.result_type == 'nzb':
                    if not nzb.provider.login():
                        return False

                    # TODO: Check if this needs exception handling
                    data = nzb.provider.session(nzb.url).content
                    if data is None:
                        return False

                    nzbcontent64 = standard_b64encode(data).decode()

                nzbget_result = nzbGetRPC.append(
                    nzb.name + '.nzb',
                    category,
                    addToTop,
                    nzbcontent64
                )
        elif nzbget_version == 12:
            if nzbcontent64 is not None:
                nzbget_result = nzbGetRPC.append(
                    nzb.name + '.nzb', category, nzbgetprio, False,
                    nzbcontent64, False, dupekey, dupescore, 'score'
                )
            else:
                nzbget_result = nzbGetRPC.appendurl(
                    nzb.name + '.nzb', category, nzbgetprio, False, nzb.url,
                    False, dupekey, dupescore, 'score'
                )
        # v13+ has a new combined append method that accepts both (url and
        # content) also the return value has changed from boolean to integer
        # (Positive number representing NZBID of the queue item. 0 and negative
        # numbers represent error codes.)
        elif nzbget_version >= 13:
            nzbget_result = nzbGetRPC.append(
                nzb.name + '.nzb',
                nzbcontent64 if nzbcontent64 is not None else nzb.url,
                category, nzbgetprio, False, False, dupekey, dupescore,
                'score'
            ) > 0
        else:
            if nzbcontent64 is not None:
                nzbget_result = nzbGetRPC.append(
                    nzb.name + '.nzb', category, nzbgetprio, False,
                    nzbcontent64
                )
            else:
                nzbget_result = nzbGetRPC.appendurl(
                    nzb.name + '.nzb', category, nzbgetprio, False, nzb.url
                )

        if nzbget_result:
            log.debug('NZB sent to NZBget successfully')
            return True
        else:
            log.warning('NZBget could not add {name}.nzb to the queue',
                        {'name': nzb.name})
            return False
    except Exception:
        log.warning('Connect Error to NZBget: could not add {name}.nzb to the'
                    ' queue', {'name': nzb.name})
        return False
