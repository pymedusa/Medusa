# coding=utf-8

"""Rss feed Generator."""

from __future__ import unicode_literals

import logging
import os
import time
import xml.etree.ElementTree as ElemTree
from datetime import datetime, timedelta

from medusa import app
from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


XMLNS = {'medusa': 'https://pymedusa.com'}


def add_result_to_feed(result):
    """
    Adds search result and metadata to rss feed.

    :return: bool representing success
    """
    for k, v in XMLNS.items():
        ElemTree.register_namespace(k, v)

    file_path = os.path.join(app.RSS_DIR, u'medusa.xml')

    if result.provider is None:
        log.error(u'Invalid provider name - this is a coding error, report it please')
        return False

    root_element = _read_existing_xml(file_path)

    if root_element is None:
        return False

    channel_element = _find_channel_element(root_element)
    if channel_element is None:
        return False

    item_start_index = _find_item_start_index(channel_element)
    channel_element.insert(item_start_index, _result_to_item(result))
    while len(channel_element) > app.RSS_MAX_ITEMS:
        channel_element.remove(channel_element[-1])

    return _write_xml(root_element, file_path)


def __element(name, text, **attribs):
    """
    Creates xml element with the given data.

    Basically just ElemTree.Element() but assigns text
    Example:
        <name attribK1="attribV1" attribK2="attribV2">text</name>

    :return: ElemTree.Element
    """
    elem = ElemTree.Element(name, attribs)
    elem.text = str(text) if text is not None else ''
    return elem


def _pubdate():
    """
    Generates pubdate according to rss standard format eg "Mon, 02 Mar 2004 05:06:07 GMT".

    :return: string
    """
    return (datetime.now() + timedelta(hours=time.timezone / 3600)).strftime('%a, %d %b %Y %H:%M:%S') + ' GMT'


def _result_to_item(result):
    """
    Populates xml element 'item' with child elements using metadata from result.

    :return: ElemTree.Element
    """
    item_root = __element('item', None)
    item_root.append(__element('title', result.name))
    item_root.append(__element('link', result.url))
    item_root.append(__element('guid', result.identifier, isPermalink='false'))
    item_root.append(__element('pubDate', _pubdate()))
    if len(result.episodes) == 1:
        item_root.append(__element('description', f'{result.episodes[0].name} | {result.episodes[0].description}'))
    else:
        item_root.append(__element('description', result.name))
    item_root.append(__element('enclosure', None, url=result.url, length='0', type='application/x-bittorrent' if result.result_type else 'application/x-nzb'))
    item_root.append(__element('medusa:series',
                               result.series.name,
                               isAnime=str(result.series.anime),
                               tvdb=str(result.series.tvdb_id),
                               imdb=result.series.imdb_id))
    item_root.append(__element('medusa:season', result.actual_season))
    item_root.append(__element('medusa:episode', result.actual_episode))
    item_root.append(__element('medusa:provider', result.provider.name))

    return item_root


def _find_item_start_index(channel_element):
    """
    Finds index of the last child that isn't a <item>.

    :return: int
    """
    for i, child in enumerate(channel_element):
        if child.tag == 'item':
            return i
    return len(channel_element)


def _read_existing_xml(file_path):
    """
    Reads xml from disk or creates a new xml from template.

    :return: ElemTree.Element root
    """
    if not os.path.isfile(file_path):
        root = _make_empty_xml()
        if not _write_xml(root, file_path):
            return None
        return root

    try:
        with open(file_path, 'r') as f:
            xml_string = f.read()
    except OSError as e:
        log.error(u'Error reading RSS file at {0}: {1}', file_path, ex(e))
    try:
        root = ElemTree.fromstring(xml_string)
        return root
    except ElemTree.ParseError as e:
        log.error(u'Error parsing RSS file at {0}: {1}', file_path, ex(e))
        return None


def _make_empty_xml():
    """
    Builds empty xml template.

    :return: ElemTree.Element root 'rss' element
    """
    root = ElemTree.Element('rss')
    for k, v in XMLNS.items():
        root.attrib['xmlns:' + k] = v
    root.attrib['version'] = '2.0'
    root.append(__element('title', 'Medusa RSS Feed'))
    root.append(__element('link', 'https://pymedusa.com/'))
    root.append(__element('description', 'Medusa RSS Feed'))
    root.append(__element('channel', None))
    return root


def _write_xml(root_element, file_path):
    """
    Writes rss xml file to disk.

    :return: bool representing success
    """
    try:
        xml_string = ElemTree.tostring(root_element, encoding='unicode')
        xml_string = xml_string.replace('\n', '')
        with open(file_path, 'w') as f:
            f.write(xml_string)
        return True
    except OSError as e:
        log.error(u'Error writing RSS file at {0}: {1}', file_path, ex(e))
        return False


def _find_channel_element(root_element):
    """
    Finds channel element in xml.

    :return: ElemTree.Element channel
    """
    return root_element.find('channel')
