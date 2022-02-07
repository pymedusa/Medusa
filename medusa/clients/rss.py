# coding=utf-8

"""Rss feed Generator."""

from __future__ import unicode_literals

import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.helper.exceptions import ex

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

XMLNS = {'medusa': 'https://pymedusa.com'}


class rss():
    """RSS class."""

    def __init__(self):
        self.OUT_FILE = os.path.join(app.RSS_DIR, u'medusa.xml')

        for k, v in XMLNS.items():
            ET.register_namespace(k, v)

    def __element(self, name, text, **attribs):
        """
        Creates xml element with the given data
        Basically just ET.Element() but assigns text
        Example:
            <name attribK1="attribV1" attribK2="attribV2">text</name>

        :return: ET.Element
        """
        elem = ET.Element(name, attribs)
        elem.text = str(text) if text is not None else ""
        return elem

    def _pubdate(self):
        """
        Generates pubdate according to rss standard format eg "Mon, 02 Mar 2004 05:06:07 GMT"

        :return: string
        """
        return (datetime.now() + timedelta(hours=time.timezone / 3600)).strftime('%a, %d %b %Y %H:%M:%S') + ' GMT'

    def _result_to_item(self, result):
        """
        Populates xml element 'item' with child elements using metadata from result

        :return: ET.Element
        """
        item_root = self.__element('item', None)
        item_root.append(self.__element('title', result.name))
        item_root.append(self.__element('link', result.url))
        item_root.append(self.__element('guid', result.identifier, isPermalink='false'))
        item_root.append(self.__element('pubDate', self._pubdate()))
        if len(result.episodes) == 1:
            item_root.append(self.__element('description', f'{result.episodes[0].name} | {result.episodes[0].description}'))
        else:
            item_root.append(self.__element('description'), result.name)
        item_root.append(self.__element('enclosure', None, url=result.url, length='0', type='application/x-bittorrent' if result.result_type else 'application/x-nzb'))
        item_root.append(self.__element('medusa:series', result.series.name, isAnime=str(result.series.anime), tvdb=str(result.series.tvdb_id), imdb=result.series.imdb_id))
        item_root.append(self.__element('medusa:season', result.actual_season))
        item_root.append(self.__element('medusa:episode', result.actual_episode))
        item_root.append(self.__element('medusa:provider', result.provider.name))

        return item_root

    def add_result_to_feed(self, result):
        """
        Adds search result and metadata to rss feed

        :return: bool representing success
        """
        if result.provider is None:
            log.error(u'Invalid provider name - this is a coding error, report it please')
            return False

        root_element = self._read_existing_xml()

        if root_element is None:
            return False

        channel_element = self._find_channel_element(root_element)
        if channel_element is None:
            return False

        item_start_index = self._find_item_start_index(channel_element)
        channel_element.insert(item_start_index, self._result_to_item(result))
        while len(channel_element) > app.RSS_MAX_ITEMS:
            channel_element.remove(channel_element[-1])

        return self._write_xml(root_element)

    def _find_item_start_index(self, channel_element):
        """
        Finds index of the last child that isn't a <item>

        :return: int
        """
        for i, child in enumerate(channel_element):
            if child.tag == 'item':
                return i
        return len(channel_element)

    def _read_existing_xml(self):
        """
        Reads xml from disk or creates a new xml from template

        :return: ET.Element root
        """
        if not os.path.isfile(self.OUT_FILE):
            root = self._make_empty_xml()
            if not self._write_xml(root):
                return None
            return root

        try:
            with open(self.OUT_FILE, 'r') as f:
                xml_string = f.read()
        except OSError as e:
            log.error(u'Error reading RSS file at {0}: {1}', self.OUT_FILE, ex(e))
        try:
            root = ET.fromstring(xml_string)
            return root
        except ET.ParseError as e:
            log.error(u'Error parsing RSS file at {0}: {1}', self.OUT_FILE, ex(e))
            return None

    def _make_empty_xml(self):
        """
        Builds empty xml template

        :return: ET.Element root 'rss' element
        """
        root = ET.Element('rss')
        for k, v in XMLNS.items():
            root.attrib['xmlns:' + k] = v
        root.attrib['version'] = '2.0'
        root.append(self.__element('title', 'Medusa RSS Feed'))
        root.append(self.__element('link', 'https://pymedusa.com/'))
        root.append(self.__element('description', 'Medusa RSS Feed'))
        root.append(self.__element('channel', None))
        return root

    def _write_xml(self, root_element):
        """
        Writes rss xml file to disk

        :return: bool representing success
        """
        try:
            xml_string = ET.tostring(root_element, encoding='unicode')
            xml_string = xml_string.replace('\n', '')
            with open(self.OUT_FILE, 'w') as f:
                f.write(xml_string)
            return True
        except OSError as e:
            log.error(u'Error writing RSS file at {0}: {1}', self.OUT_FILE, ex(e))
            return False

    def _find_channel_element(self, root_element):
        """
        Finds channel element in xml

        :return: ET.Element channel
        """
        return root_element.find('channel')
