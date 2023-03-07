import os
import re
import medusa
import xml.etree.ElementTree as ElemTree
from medusa.clients import rss


EXPECTED_RAW_TEXT = """<rss xmlns:medusa="https://pymedusa.com" version="2.0"><title>Medusa RSS Feed</title><link>https://pymedusa.com/</link><description>
Medusa RSS Feed</description><channel><item><title>test_release_name</title><link>https://test_provider.com/test_result.url</link><guid isPermalink="false">
test_guid</guid><description>test_episode_name | test_episode_description</description><enclosure url="https://test_provider.com/test_result.url" length="0"
 type="application/x-bittorrent" /><medusa:series isAnime="test_is_anime" tvdb="test_tvdbid" imdb="test_imdbid">test_series_name</medusa:series><medusa:season>
test_actual_season</medusa:season><medusa:episode>test_actual_episode</medusa:episode><medusa:provider>test_provider</medusa:provider></item></channel></rss>"""


class AnonymousClass:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def _result():
    r = medusa.classes.SearchResult('test_provider', 'test_series')
    r.name = 'test_release_name'
    r.url = 'https://test_provider.com/test_result.url'
    r.episodes = [AnonymousClass(name='test_episode_name', description='test_episode_description')]
    r.season = 'test_season'
    r.episode = 'test_episode_name'
    r.series = AnonymousClass(name='test_series_name', anime='test_is_anime', tvdb_id='test_tvdbid', imdb_id='test_imdbid')
    r.actual_season = 'test_actual_season'
    r.actual_episode = 'test_actual_episode'
    r.provider = AnonymousClass(name='test_provider', identifier='test_guid', _get_identifier=lambda _: 'test_guid')
    r.result_type = 'torrent'
    return r


def test_add_result_to_feed():
    """
    This isn't a fantastic test, but it confirms that the rss xml is properly formed.
    """
    medusa.app.RSS_DIR = './'
    file_path = os.path.join(medusa.app.RSS_DIR, u'medusa.xml')

    rss.add_result_to_feed(_result())

    with open(file_path, 'r') as f:
        rss_raw_text = f.read()
    os.unlink(file_path)
    rss_raw_text = re.sub(r'<pubDate>(.*)<\/pubDate>', '', rss_raw_text)

    result_et = ElemTree.fromstring(rss_raw_text)
    expected_et = ElemTree.fromstring(EXPECTED_RAW_TEXT.replace('\n', ''))

    for (e1, e2) in zip(result_et, expected_et):
        elements_equal(e1, e2)


def elements_equal(elem1, elem2):
    """
    Recursively asserts equality between elementtree elements and children.
    """
    assert elem1.tag == elem2.tag
    assert elem1.text == elem2.text
    assert elem1.tail == elem2.tail
    assert elem1.attrib == elem2.attrib
    assert len(elem1) == len(elem2)
    for (e1, e2) in zip(elem1, elem2):
        elements_equal(e1, e2)
