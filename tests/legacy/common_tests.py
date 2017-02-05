# coding=utf-8

"""Unit Tests for common package."""

from __future__ import print_function

import unittest

from medusa import common


class QualityStringTests(unittest.TestCase):
    """Test Case for strings in common.Quality."""

    test_cases = {
        'sd_tv': [
            "Test.Show.S01E02.PDTV.XViD-GROUP",
            "Test.Show.S01E02.PDTV.x264-GROUP",
            "Test.Show.S01E02.HDTV.XViD-GROUP",
            "Test.Show.S01E02.HDTV.x264-GROUP",
            "Test.Show.S01E02.DSR.XViD-GROUP",
            "Test.Show.S01E02.DSR.x264-GROUP",
            "Test.Show.S01E02.TVRip.XViD-GROUP",
            "Test.Show.S01E02.TVRip.x264-GROUP",
            "Test.Show.S01E02.WEBRip.XViD-GROUP",
            "Test.Show.S01E02.WEBRip.x264-GROUP",
            "Test.Show.S01E02.WEB-DL.x264-GROUP",
            "Test.Show.S01E02.WEB-DL.AAC2.0.H.264-GROUP",
            "Test.Show.S01E02 WEB-DL H 264-GROUP",
            "Test.Show.S01E02_WEB-DL_H_264-GROUP",
            "Test.Show.S01E02.WEB-DL.AAC2.0.H264-GROUP"
        ],
        'sd_dvd': [
            "Test.Show.S01E02.480P.DVDrip.HEVC.X265",
            "Test.Show.S01E02.DVDRiP.XViD-GROUP",
            "Test.Show.S01E02.DVDRiP.DiVX-GROUP",
            "Test.Show.S01E02.DVDRiP.x264-GROUP",
            "Test.Show.S01E02.DVDRip.WS.XViD-GROUP",
            "Test.Show.S01E02.DVDRip.WS.DiVX-GROUP",
            "Test.Show.S01E02.DVDRip.WS.x264-GROUP",
            "Test.Show.S01E02.BDRIP.XViD-GROUP",
            "Test.Show.S01E02.BDRIP.DiVX-GROUP",
            "Test.Show.S01E02.BDRIP.x264-GROUP",
            "Test.Show.S01E02.BDRIP.WS.XViD-GROUP",
            "Test.Show.S01E02.BDRIP.WS.DiVX-GROUP",
            "Test.Show.S01E02.BDRIP.WS.x264-GROUP"
        ],
        'hd_tv': [
            "Test.Show.S01E02.720p.HDTV.x264-GROUP",
            "Test.Show.S01E02.HR.WS.PDTV.x264-GROUP"
        ],
        'raw_hd_tv': [
            "Test.Show.S01E02.720p.HDTV.DD5.1.MPEG2-GROUP",
            "Test.Show.S01E02.1080i.HDTV.DD2.0.MPEG2-GROUP",
            "Test.Show.S01E02.1080i.HDTV.H.264.DD2.0-GROUP",
            "Test Show - S01E02 - 1080i HDTV MPA1.0 H.264 - GROUP",
            "Test.Show.S01E02.1080i.HDTV.DD.5.1.h264-GROUP"
        ],
        'full_hd_tv': [
            "Test.Show.S01E02.1080p.HDTV.x264-GROUP"
        ],
        'hd_web_dl': [
            "Test.Show.S01E02.720p.WEB-DL-GROUP",
            "Test.Show.S01E02.720p.WEBRip-GROUP",
            "Test.Show.S01E02.WEBRip.720p.H.264.AAC.2.0-GROUP",
            "Test.Show.S01E02.720p.WEB-DL.AAC2.0.H.264-GROUP",
            "Test Show S01E02 720p WEB-DL AAC2 0 H 264-GROUP",
            "Test_Show.S01E02_720p_WEB-DL_AAC2.0_H264-GROUP",
            "Test.Show.S01E02.720p.WEB-DL.AAC2.0.H264-GROUP",
            "Test.Show.S01E02.720p.iTunes.Rip.H264.AAC-GROUP"
        ],
        'full_hd_web_dl': [
            "Test.Show.S01E02.1080p.WEB-DL-GROUP",
            "Test.Show.S01E02.1080p.WEBRip-GROUP",
            "Test.Show.S01E02.WEBRip.1080p.H.264.AAC.2.0-GROUP",
            "Test.Show.S01E02.WEBRip.1080p.H264.AAC.2.0-GROUP",
            "Test.Show.S01E02.1080p.iTunes.H.264.AAC-GROUP",
            "Test Show S01E02 1080p iTunes H 264 AAC-GROUP",
            "Test_Show_S01E02_1080p_iTunes_H_264_AAC-GROUP"
        ],
        'hd_bluray': [
            "Test.Show.S01E02.720p.BluRay.x264-GROUP",
            "Test.Show.S01E02.720p.HDDVD.x264-GROUP"
        ],
        'full_hd_bluray': [
            "Test.Show.S01E02.1080p.BluRay.x264-GROUP",
            "Test.Show.S01E02.1080p.HDDVD.x264-GROUP"
        ],
        'unknown': [
            "Test.Show.S01E02-SomeGroup",
            "Test.Show.S01E01-20.1080i.[Mux.-.1080i.-.H264.-.Ac3.].HDTVMux.GROUP",
        ],
    }

    def test_sd_tv(self):
        cur_test = 'sd_tv'
        cur_qual = common.Quality.SDTV

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_sd_dvd(self):
        cur_test = 'sd_dvd'
        cur_qual = common.Quality.SDDVD

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_hd_tv(self):
        cur_test = 'hd_tv'
        cur_qual = common.Quality.HDTV

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_raw_hd_tv(self):
        cur_test = 'raw_hd_tv'
        cur_qual = common.Quality.RAWHDTV

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_full_hd_tv(self):
        cur_test = 'full_hd_tv'
        cur_qual = common.Quality.FULLHDTV

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_hd_web_dl(self):
        cur_test = 'hd_web_dl'
        cur_qual = common.Quality.HDWEBDL

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_full_hd_web_dl(self):
        cur_test = 'full_hd_web_dl'
        cur_qual = common.Quality.FULLHDWEBDL

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_hd_bluray(self):
        cur_test = 'hd_bluray'
        cur_qual = common.Quality.HDBLURAY

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_full_hd_bluray(self):
        cur_test = 'full_hd_bluray'
        cur_qual = common.Quality.FULLHDBLURAY

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_unknown(self):
        cur_test = 'unknown'
        cur_qual = common.Quality.UNKNOWN

        for name, tests in self.test_cases.items():
            for test in tests:
                if name == cur_test:
                    self.assertEqual(cur_qual, common.Quality.name_quality(test))
                else:
                    self.assertNotEqual(cur_qual, common.Quality.name_quality(test))

    def test_anime(self):
        test_cases = {
            'sd_dvd': [
                '[DeadFish].Shingeki.no.Kyojin.-.01.-.OVA.[DVD][480p][AAC].mp4',
            ],
            'full_hd_bluray': [
                '[Hatsuyuki-Kaitou]_Shingeki_no_Kyojin_-_Special_02_[BD_1080p][10bit][FLAC][4D908801].mkv',
            ],
        }
        test_quality = {
            'sd_tv': common.Quality.SDTV,
            'sd_dvd': common.Quality.SDDVD,
            'raw_hd_tv': common.Quality.RAWHDTV,
            'hd_tv': common.Quality.HDTV,
            'hd_web_dl': common.Quality.HDWEBDL,
            'hd_bluray': common.Quality.HDBLURAY,
            'full_hd_tv': common.Quality.FULLHDTV,
            'full_hd_web_dl': common.Quality.FULLHDWEBDL,
            'full_hd_bluray': common.Quality.FULLHDBLURAY,
            'unknown': common.Quality.UNKNOWN,
        }
        for cur_test, expected_qual in test_quality.items():
            for qual, tests in test_cases.items():
                for name in tests:
                    if qual == cur_test:
                        self.assertEqual(expected_qual, common.Quality.name_quality(name, anime=True),
                                         (qual, name, expected_qual, common.Quality.name_quality(name, anime=True)))
                    else:
                        self.assertNotEqual(expected_qual, common.Quality.name_quality(name, anime=True),
                                            (qual, name, expected_qual, common.Quality.name_quality(name, anime=True)))


class QualityTests(unittest.TestCase):
    """Test Case for common.Quality."""

    # TODO: repack / proper ? air-by-date ? season rip? multi-ep?
    @unittest.expectedFailure
    # reverse parsing does not work
    def test_reverse_parsing(self):
        tests = [
            (common.Quality.SDTV, "Test Show - S01E02 - SDTV - GROUP"),
            (common.Quality.SDDVD, "Test Show - S01E02 - SD DVD - GROUP"),
            (common.Quality.HDTV, "Test Show - S01E02 - HDTV - GROUP"),
            (common.Quality.RAWHDTV, "Test Show - S01E02 - RawHD - GROUP"),
            (common.Quality.FULLHDTV, "Test Show - S01E02 - 1080p HDTV - GROUP"),
            (common.Quality.HDWEBDL, "Test Show - S01E02 - 720p WEB-DL - GROUP"),
            (common.Quality.FULLHDWEBDL, "Test Show - S01E02 - 1080p WEB-DL - GROUP"),
            (common.Quality.HDBLURAY, "Test Show - S01E02 - 720p BluRay - GROUP"),
            (common.Quality.FULLHDBLURAY, "Test Show - S01E02 - 1080p BluRay - GROUP"),
            (common.Quality.UNKNOWN, "Test Show - S01E02 - Unknown - SomeGroup"),
        ]
        for test in tests:
            quality, test = test
            self.assertEqual(quality, common.Quality.name_quality(test),
                             (quality, common.Quality.name_quality(test), test))


class StatusStringsTests(unittest.TestCase):
    """Test Case for common.StatusStrings."""

    # TODO: Split tests into separate tests and add additional tests
    def test_all(self):
        status_strings = common.statusStrings

        valid = 1, 112, '1', '112'
        unused = 122, 99998989899878676, '99998989899878676', None
        invalid = 'Elephant', (4, 1), [1, 233, 4, None]

        for i in valid:
            self.assertTrue(i in status_strings)

        for i in unused:
            self.assertFalse(i in status_strings)
            with self.assertRaises(KeyError):
                self.assertTrue(status_strings[i])

        for i in status_strings:
            self.assertEqual(status_strings[i], status_strings[str(i)])
            self.assertEqual(i in status_strings, str(i) in status_strings)

        for i in status_strings.qualities:
            self.assertEqual(status_strings[i], status_strings[str(i)])
            self.assertEqual(i in status_strings, str(i) in status_strings)

        for i in invalid:
            with self.assertRaises(TypeError):
                status_strings[i] = 1

        for i in unused:
            if i is None:
                with self.assertRaises(TypeError):
                    status_strings[str(i)] = 1  # 'None' is not None
                status_strings[i] = 1  # ...but None can still be used as a key
            else:
                status_strings[str(i)] = 1
            self.assertEqual(status_strings[i], 1)


class OverviewTests(unittest.TestCase):
    """Test common.Overview."""

    def test_overview_strings(self):
        overview = common.Overview()

        self.assertEqual(overview.overviewStrings[overview.SKIPPED], "skipped")
        self.assertEqual(overview.overviewStrings[overview.WANTED], "wanted")
        self.assertEqual(overview.overviewStrings[overview.QUAL], "qual")
        self.assertEqual(overview.overviewStrings[overview.GOOD], "good")
        self.assertEqual(overview.overviewStrings[overview.UNAIRED], "unaired")
        self.assertEqual(overview.overviewStrings[overview.SNATCHED], "snatched")
