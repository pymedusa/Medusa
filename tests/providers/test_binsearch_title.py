# coding=utf-8
"""Title parse test code for Binsearch Provider."""
from __future__ import unicode_literals

from medusa.providers.nzb.binsearch import BinSearchProvider
import pytest


@pytest.mark.parametrize('p', [
    {  # p0: None
        'title': '[ 160929_02 Arrow.S05E02.1080p.AMZN.WEBRip.DD5.1.x264-NTb ] - [1/1] - "160929_02 Arrow.S05E02.The.'
                 'Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb.nfo" yEnc (1/1)',
        'mode': 'episode',
        'expected': 'Arrow.S05E02.The.Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb'
    },
    {  # p0: None
        'title': 'AMS Arrow.S05E02.The.Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb [01/55] - "Arrow.S05E02.The.Recruits.'
                 '1080p.AMZN.WEBRip.DD5.1.x264-NTb.par2" yEnc (1/1)',
        'mode': 'episode',
        'expected': 'Arrow.S05E02.The.Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb'
    },
    {  # p0: None
        'title': 'Arrow S05E02 [1 of 15] "Arrow.S05E02.FRENCH.WEBRip.XviD.avi.part.par2" yEnc (1/1)collection size: '
                 '358.31 MB, parts available: 1041 / 1041- 7 rar files- 1 par2 file',
        'mode': 'episode',
        'expected': 'Arrow.S05E02.FRENCH.WEBRip.XviD.avi'
    },
    {  # p0: None
        'title': '(????) [013/275] - "Arrow.S05E02.HDTV.HebSubs.XviD-AFG.par2" yEnc (1/1)collection size: 506.17 MB, '
                 'parts available: 1344 / 1344- 9 par2 files- 3 rar files',
        'mode': 'episode',
        'expected': 'Arrow.S05E02.HDTV.HebSubs.XviD-AFG'
    },
    {  # p0: None
        'title': '[382187]-[FULL]-[#[email protected]]-[ Architects.Of.F1.S01E02.Gordon.Murray.1080p.HDTV.x264-GRiP ]'
                 '-[01/23] - "architects.of.f1.s01e02.gordon.murray.1080p.hdtv.x264-grip.nfo" yEnc (1/1)collection size: '
                 '2.39 GB, parts available: 3247 / 3247- 8 par2 files- 12 rar files- 1 srr file- 1 sfv file- 1 nfo fileview NFO',
        'mode': 'episode',
        'expected': 'architects.of.f1.s01e02.gordon.murray.1080p.hdtv.x264-grip'
    },
    {  # p0: None
        'title': '(1/1) - Description - "The.Grand.Tour.S01E01.720p.HEVC.X265-M!B[S1n].nzb" - 418.22 kB - yEnc (1/2)'
                 'collection size: 855.66 KB, parts available: 5 / 5- 2 nzb files- 1 nfo fileview NFO',
        'mode': 'episode',
        'expected': 'The.Grand.Tour.S01E01.720p.HEVC.X265-M!B[S1n]'
    },
    {  # p0: None
        'title': 'grandtour - [00/20] - "The.Grand.Tour.S01E01.WEBRip.X264-DEFLATE[ettv].nzb" yEnc (1/1)collection size: '
                 '1.12 GB, parts available: 3037 / 3037- 10 par2 files- 10 rar files- 1 nzb file',
        'mode': 'episode',
        'expected': 'The.Grand.Tour.S01E01.WEBRip.X264-DEFLATE[ettv]'
    },
    {  # p0: None
        'title': '[ TrollHD ] - [ 000/343 ] - "The Grand Tour S01E01 2160p Amazon WEBRip DD+ 5.1 x264-TrollUHD.nzb" '
                 'yEnc (1/10)collection size: 34.68 GB, parts available: 56365 / 56365- unidentified files (note to '
                 'poster: put quotes around the filename in the subject)- 72 par2 files- 1 nzb file',
        'mode': 'episode',
        'expected': 'The Grand Tour S01E01 2160p Amazon WEBRip DD+ 5.1 x264-TrollUHD'
    },
    {  # p0: None
        'title': '[00/65] - "The.Grand.Tour.S01E01.German.WebHD-720p.x264.nzb" yEnc (1/3)collection size: 3.04 GB, parts '
                 'available: 8245 / 8245- 9 par2 files- 55 rar files- 1 nfo file- 1 nzb fileview NFO',
        'mode': 'episode',
        'expected': 'The.Grand.Tour.S01E01.German.WebHD-720p.x264'
    },
    {  # p0: None
        'title': '[ TOWN ]-[ www.town.ag ]-[ partner of www.ssl-news.info ]-[ OPEN ] [01/16] - "The.Passing.Bells.'
                 'S01E01.720p.HDTV.x264-TASTETV.par2" - 555,41 MB yEnc (1/1)collection size: 576.49 MB, parts available:'
                 ' 1522 / 1522- 4 par2 files- 11 rar files- 1 nfo fileview NFO',
        'mode': 'episode',
        'expected': 'The.Passing.Bells.S01E01.720p.HDTV.x264-TASTETV'
    },
    {  # p0: None
        'title': '"Sense8 S01 MULTi 1080p WEBRip DD5 1 H 264-IMPERIUM.zip" yEnc (1/1)',
        'mode': 'episode',
        'expected': 'Sense8 S01 MULTi 1080p WEBRip DD5 1 H 264-IMPERIUM'
    },
    {  # p0: None
        'title': 'pFyLzeqxIhLQS5qdjCuHXBYOgqRb5A - [887/998] - "Selfie S01E01.part1.rar" yEnc (1/82)collection size:'
                 ' 88.54 MB, parts available: 234 / 234- 3 rar files',
        'mode': 'episode',
        'expected': 'Selfie S01E01.part1'
    },
    {  # p0: None
        'title': '[PRiVATE] Murdered.For.Her.Selfies.S01E01.WEB.h264-ROFL [newzNZB] [1/7] - "murdered.for.her.'
                 'selfies.s01e01.web.h264-rofl.nfo" yEnc (1/1)collection size: 90.87 MB, parts available: 126 / '
                 '126- 1 sfv file- 5 rar files- 1 nfo fileview NFO',
        'mode': 'episode',
        'expected': 'murdered.for.her.selfies.s01e01.web.h264-rofl'
    }
])
def test_parse_binsearch_title(p):
    # Given
    title = p['title']
    mode = p['mode']
    expected = p['expected']

    # When
    actual = BinSearchProvider.clean_title(title, mode)

    # Then
    assert expected == actual
