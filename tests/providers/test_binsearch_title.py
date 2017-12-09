from medusa.providers.nzb.binsearch import BinSearchProvider

import pytest


@pytest.mark.parametrize('p', [
    {  # p0: None
        'title': '[ 160929_02 Arrow.S05E02.1080p.AMZN.WEBRip.DD5.1.x264-NTb ] - [1/1] - "160929_02 Arrow.S05E02.The.Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb.nfo" yEnc (1/1)',
        'mode': 'episode',
        'expected': 'Arrow.S05E02.The.Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb'
    },
    {  # p0: None
        'title': 'AMS Arrow.S05E02.The.Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb [01/55] - "Arrow.S05E02.The.Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb.par2" yEnc (1/1)',
        'mode': 'episode',
        'expected': 'Arrow.S05E02.The.Recruits.1080p.AMZN.WEBRip.DD5.1.x264-NTb'
    },
    {  # p0: None
        'title': 'Arrow S05E02 [1 of 15] "Arrow.S05E02.FRENCH.WEBRip.XviD.avi.part.par2" yEnc (1/1)collection size: 358.31 MB, parts available: 1041 / 1041- 7 rar files- 1 par2 file',
        'mode': 'episode',
        'expected': u'Arrow.S05E02.FRENCH.WEBRip.XviD.avi'
    },
    {  # p0: None
        'title': '(????) [013/275] - "Arrow.S05E02.HDTV.HebSubs.XviD-AFG.par2" yEnc (1/1)collection size: 506.17 MB, parts available: 1344 / 1344- 9 par2 files- 3 rar files',
        'mode': 'episode',
        'expected': 'Arrow.S05E02.HDTV.HebSubs.XviD-AFG'
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
