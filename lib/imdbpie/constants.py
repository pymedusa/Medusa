from __future__ import absolute_import, unicode_literals

import hashlib

BASE_URI = 'https://app.imdb.com'
API_KEY = '2wex6aeu6a8q9e49k7sfvufd6rhh0n'
SHA1_KEY = hashlib.sha1(API_KEY.encode('utf8')).hexdigest()
USER_AGENTS = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) '
    'AppleWebKit/534.46 (KHTML, like Gecko) Mobile/9A334',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) AppleWebKit/534.46 '
    '(KHTML, like Gecko) Version/5.1 Mobile/9A334 Safari/7534.48.3',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0_1 like Mac OS X) AppleWebKit/'
    '534.46 (KHTML, like Gecko) Mobile/9A405',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0_1 like Mac OS X) AppleWebKit/'
    '534.46 (KHTML, like Gecko) Mobile/9A406',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0_1 like Mac OS X) AppleWebKit/'
    '534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A405 Safari/7534.48.3',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0_1 like Mac OS X) AppleWebKit/'
    '534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A406 Safari/7534.48.3',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/'
    '534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B179 Safari/7534.48.3',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_1_1 like Mac OS X) AppleWebKit/534'
    '.46 (KHTML, like Gecko) Version/5.1 Mobile/9B206 Safari/7534.48.3',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26'
    ' (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_2 like Mac OS X) AppleWebKit/53'
    '6.26 (KHTML, like Gecko) Version/6.0 Mobile/10B146 Safari/8536.25',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_3 like Mac OS X) AppleWebKit/'
    '536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B329 Safari/8536.25',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_4 like Mac OS X) AppleWebKit/'
    '536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B350 Safari/8536.25',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) AppleWebKit/'
    '537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_3 like Mac OS X) AppleWebKit/'
    '537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B511 Safari/9537.53',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_4 like Mac OS X) AppleWebKit/'
    '537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B554a Safari/9537.53',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_6 like Mac OS X) AppleWebKit/'
    '537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B651 Safari/9537.53',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) AppleWebKit/'
    '537.51.2 (KHTML, like Gecko) Version/7.0 Mobile/11D167 Safari/9537.53',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 7_1_1 like Mac OS X) AppleWebKit/'
    '537.51.2 (KHTML, like Gecko) Version/7.0 Mobile/11D201 Safari/9537.53',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 8_0_2 like Mac OS X) AppleWebKit/'
    '600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12A366 Safari/600.1.4'
    'Mozilla/5.0 (iPhone; CPU iPhone OS 8_0 like Mac OS X) AppleWebKit/600.1.4'
    ' (KHTML, like Gecko) Version/8.0 Mobile/12A366 Safari/600.1.4',
    'Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebK'
    'it/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16',
    'Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_0 like Mac OS X; en-us) AppleWebK'
    'it/532.9 (KHTML, like Gecko) Version/4.0.5 Mobile/8A293 Safari/6531.22.7',
    'Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) AppleWe'
    'bKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 '
    'Mobile/8H7 Safari/6533.18.5',
    'Mozilla/5.0 (iPod; CPU iPhone OS 6_1_3 like Mac OS X) AppleWebKit/536.26 '
    '(KHTML, like Gecko) Version/6.0 Mobile/10B329 Safari/8536.25',
    'Mozilla/5.0 (iphone; U; CPU iPhone OS 4_3_5 like Mac OS X; zh-cn) AppleWe'
    'bKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 '
    'Mobile/8J2 Safari/6533.18.5',
    'Mozilla/5.0 (iphone; cpu iphone os 7_0_2 like mac os x) Applewebkit/537.5'
    '1.1 (khtml, like gecko) version/7.0 mobile/11a501 safari/9537.53',
    'Mozilla/5.0(iPhone; U; CPU iPhone OS 4_1 like Mac OS X; en-us)AppleWebKit'
    '/532.9 (KHTML, like Gecko) Version/4.0.5 Mobile/8B5097d Safari/6531.22.7',
    'Mozilla/5.0(iPhone;U;CPUiPhoneOS4_0likeMacOSX;en-us)AppleWebKit/532.9(KHT'
    'ML,likeGecko)Version/4.0.5Mobile/8A293Safari/6531.22.7'
)
DEFAULT_PROXY_URI = 'http://openwebproxy.pw/browse.php?u={0}'
