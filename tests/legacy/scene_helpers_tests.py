# coding=utf-8
"""Test scene helpers."""

import unittest

from medusa import common, db, name_cache, scene_exceptions, show_name_helpers
from medusa.tv import TVShow as Show
from . import test_lib as test


class SceneTests(test.AppTestDBCase):
    """Test Scene."""

    def _test_all_possible_show_names(self, name, indexerid=0, expected=None):
        """Test all possible show names.

        :param name:
        :param indexerid:
        :param expected:
        :return:
        """
        expected = [] if expected is None else expected
        show = Show(1, indexerid)
        show.name = name

        result = show_name_helpers.allPossibleShowNames(show)
        self.assertTrue(len(set(expected).intersection(set(result))) == len(expected))

    def _test_filter_bad_releases(self, name, expected):
        """Test filter of bad releases.

        :param name:
        :param expected:
        :return:
        """
        result = show_name_helpers.filterBadReleases(name)
        self.assertEqual(result, expected)

    def test_all_possible_show_names(self):
        # common.sceneExceptions[-1] = ['Exception Test']
        test_cache_db_con = db.DBConnection('cache.db')
        test_cache_db_con.action("INSERT INTO scene_exceptions (indexer, indexer_id, show_name, season) "
                                 "VALUES (?,?,?,?)", [1, -1, 'Exception Test', -1])
        common.countryList['Full Country Name'] = 'FCN'

        self._test_all_possible_show_names('Show Name', expected=['Show Name'])
        self._test_all_possible_show_names('Show Name', -1, expected=['Show Name', 'Exception Test'])
        self._test_all_possible_show_names('Show Name FCN', expected=['Show Name FCN', 'Show Name (Full Country Name)'])
        self._test_all_possible_show_names('Show Name (FCN)', expected=['Show Name (FCN)', 'Show Name (Full Country Name)'])
        self._test_all_possible_show_names('Show Name Full Country Name', expected=['Show Name Full Country Name', 'Show Name (FCN)'])
        self._test_all_possible_show_names('Show Name (Full Country Name)', expected=['Show Name (Full Country Name)', 'Show Name (FCN)'])

    def test_filter_bad_releases(self):
        self._test_filter_bad_releases('Show.S02.SAMPLE', False)
        self._test_filter_bad_releases('Show.S02', True)
        self._test_filter_bad_releases('Show.S02.DVDEXTRAS', False)


class SceneExceptionTestCase(test.AppTestDBCase):
    """Test scene exceptions test case."""

    def setUp(self):
        """Set up tests."""
        super(SceneExceptionTestCase, self).setUp()
        scene_exceptions.retrieve_exceptions()

    def test_scene_ex_empty(self):
        self.assertEqual(scene_exceptions.get_scene_exceptions(0), [])

    @unittest.expectedFailure
    def test_scene_ex_babylon_5(self):
        self.assertEqual(sorted(scene_exceptions.get_scene_exceptions(70726)), ['Babylon 5', 'Babylon5'])

    @unittest.expectedFailure
    def test_scene_ex_by_name(self):
        self.assertEqual(scene_exceptions.get_scene_exception_by_name('Babylon5'), (70726, -1))
        self.assertEqual(scene_exceptions.get_scene_exception_by_name('babylon 5'), (70726, -1))
        self.assertEqual(scene_exceptions.get_scene_exception_by_name('Carlos 2010'), (164451, -1))

    def test_scene_ex_by_name_empty(self):
        self.assertEqual(scene_exceptions.get_scene_exception_by_name('nothing useful'), (None, None))

    def test_scene_ex_reset_name_cache(self):
        # clear the exceptions
        test_cache_db_con = db.DBConnection('cache.db')
        test_cache_db_con.action("DELETE FROM scene_exceptions")

        # put something in the cache
        name_cache.addNameToCache('Cached Name', 0)

        # updating should not clear the cache this time since our exceptions didn't change
        scene_exceptions.retrieve_exceptions()
        self.assertEqual(name_cache.retrieveNameFromCache('Cached Name'), 0)
