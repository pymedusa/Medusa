## ext
Folder | Package | Version / Commit | Used By | Notes / Modules
:----: | :-----: | :--------------: | :------ | :--------------
ext | **`adba`** | pymedusa/[37b0c74](https://github.com/pymedusa/adba/tree/37b0c74e76b40b3dbde29e71da75a1808eb121de) | **`medusa`** | -
ext | `appdirs` | [1.4.3](https://pypi.org/project/appdirs/1.4.3/) | `simpleanidb`, `subliminal` (cli only) | File: `appdirs.py`
ext | `attrs` | [18.2.0](https://pypi.org/project/attrs/18.2.0/) | `imdbpie` | Module: `attr`
ext | **`babelfish`** | [f403000](https://github.com/Diaoul/babelfish/tree/f403000dd63092cfaaae80be9f309fd85c7f20c9) | **`medusa`**, `guessit`, `knowit`, `subliminal` | -
ext | `beautifulsoup4` | [4.9.3](https://pypi.org/project/beautifulsoup4/4.9.3/) | **`medusa`**, `subliminal` | Module: `bs4`
ext | `bencode.py` | [4.0.0](https://pypi.org/project/bencode.py/4.0.0/) | **`medusa`** | Modules: `bencodepy`, `bencode`<br>Monkey-patched, see `medusa/init/__init__.py`
ext | **`boto`** | [2.48.0](https://pypi.org/project/boto/2.48.0/) | `imdbpie` | -
ext | `CacheControl` | [0.12.6](https://pypi.org/project/CacheControl/0.12.6/) | **`medusa`** | Module: `cachecontrol`
ext | **`certifi`** | [2020.12.5](https://pypi.org/project/certifi/2020.12.5/) | **`medusa`**, `requests` | -
ext | **`chardet`** | [4.0.0](https://pypi.org/project/chardet/4.0.0/) | `pysrt`, `requests`, `subliminal` | -
ext | **`cloudscraper`** | [1.2.58](https://pypi.org/project/cloudscraper/1.2.58/) | **`medusa`** | -
ext | `configobj` | [5.0.6](https://pypi.org/project/configobj/5.0.6/) | **`medusa`** | Modules: `configobj.py`, `validate.py`, `_version.py`
ext | `contextlib2` | [0.6.0.post1](https://pypi.org/project/contextlib2/0.6.0.post1/) | **`medusa`** | File: `contextlib2.py`
ext | `decorator` | [4.4.0](https://pypi.org/project/decorator/4.4.0/) | `validators` | File: `decorator.py`
ext | `deluge-client` | [1.9.0](https://pypi.org/project/deluge-client/1.9.0/) | **`medusa`** | Module: `deluge_client`
ext | **`deprecated`** | [1.2.3](https://pypi.org/project/deprecated/1.2.3/) | `PyGithub` | -
ext | **`dirtyjson`** | [1.0.7](https://pypi.org/project/dirtyjson/1.0.7/) | **`medusa`** | -
ext | **`diskcache`** | [2.9.0](https://pypi.org/project/diskcache/2.9.0/) | `imdbpie` | -
ext | `dogpile.cache` | [1.1.2](https://pypi.org/project/dogpile.cache/1.1.2/) | **`medusa`**, `subliminal` | Module: `dogpile`
ext | **`enzyme`** | pymedusa/[665cf69](https://github.com/pymedusa/enzyme/tree/665cf6948aab1c249dcc99bd9624a81d17b3302a) | `knowit`, `subliminal` | -
ext | **`feedparser`** | [6.0.2](https://pypi.org/project/feedparser/6.0.2/) | **`medusa`** | Requires `sgmllib3k` on Python 3
ext | **`gntp`** | [1.0.3](https://pypi.org/project/gntp/1.0.3/) | **`medusa`** | -
ext | **`guessit`** | [3.3.1](https://pypi.org/project/guessit/3.3.1/) | **`medusa`**, `subliminal` | -
ext | **`html5lib`** | [1.1](https://pypi.org/project/html5lib/1.1/) | **`medusa`** (via `beautifulsoup4`) | -
ext | **`idna`** | [2.8](https://pypi.org/project/idna/2.8/) | `requests` | -
ext | **`imdbpie`** | [5.6.4](https://pypi.org/project/imdbpie/5.6.4/) | **`medusa`** | -
ext | `jsonrpclib-pelix` | [0.4.2](https://pypi.org/project/jsonrpclib-pelix/0.4.2/) | **`medusa`** | Module: `jsonrpclib`
ext | **`knowit`** | [eea9ac1](https://github.com/ratoaq2/knowit/tree/eea9ac18e38c930230cf81b5dca4a9af9fb10d4e) | **`medusa`** | -
ext | `Mako` | [1.1.4](https://pypi.org/project/Mako/1.1.4/) | **`medusa`** | Module: `mako`
ext | `markdown2` | [2.4.0](https://pypi.org/project/markdown2/2.4.0/) | **`medusa`** | File: `markdown2.py`
ext | `MarkupSafe` | [1.1.1](https://pypi.org/project/MarkupSafe/1.1.1/) | `Mako` | Module: `markupsafe`
ext | **`msgpack`** | [0.5.6](https://pypi.org/project/msgpack/0.5.6/) | `CacheControl` | -
ext | **`oauthlib`** | [3.0.0](https://pypi.org/project/oauthlib/3.0.0/) | `requests-oauthlib` | -
ext | `Pint` | [0.9](https://pypi.org/project/Pint/0.9/) | `knowit` | Module: `pint`
ext | `profilehooks` | [1.12.0](https://pypi.org/project/profilehooks/1.12.0/) | **`medusa`** | File: `profilehooks.py`
ext | `PyGithub` | [1.45](https://pypi.org/project/PyGithub/1.45/) | **`medusa`** | Module: `github`
ext | `PyJWT` | [2.0.1](https://pypi.org/project/PyJWT/2.0.1/) | **`medusa`**, `PyGithub` | Module: `jwt`
ext | `pyparsing` | [2.4.7](https://pypi.org/project/pyparsing/2.4.7/) | `cloudscraper` | File: `pyparsing.py`
ext | **`pysrt`** | [1.1.0](https://pypi.org/project/pysrt/1.1.0/) | `subliminal` | -
ext | `python-dateutil` | [2.8.1](https://pypi.org/project/python-dateutil/2.8.1/) | **`medusa`**, `guessit`, `imdbpie`, `tvdbapiv2` | Module: `dateutil`
ext | `python-twitter` | [3.5](https://pypi.org/project/python-twitter/3.5/) | **`medusa`** | Module: `twitter`
ext | **`pytimeparse`** | pymedusa/[8f28325](https://github.com/pymedusa/pytimeparse/tree/8f2832597235c6ec98c44de4dab3274927f67e29) | **`medusa`** | -
ext | **`pytz`** | [2018.4](https://pypi.org/project/pytz/2018.4/) | `subliminal` | -
ext | `PyYAML` | [5.4.1](https://pypi.org/project/PyYAML/5.4.1/) | `knowit` | Modules: `_yaml`, `yaml`
ext | `rarfile` | [3.1](https://pypi.org/project/rarfile/3.1/) | **`medusa`**, `subliminal` | File: `rarfile.py`
ext | **`rebulk`** | [3.0.1](https://pypi.org/project/rebulk/3.0.1/) | **`medusa`**, `guessit` | -
ext | **`requests`** | [2.25.1](https://pypi.org/project/requests/2.25.1/) | **`medusa`**, `adba`, `boto`, `CacheControl`, `cloudscraper`, `PyGithub`, `python-twitter`, `pytvmaze`, `requests-oauthlib`, `requests-toolbelt`, `rtorrent-python`, `simpleanidb`, `subliminal`, `tmdbsimple`, `trakt`, `tvdbapiv2` | -
ext | `requests-oauthlib` | [1.3.0](https://pypi.org/project/requests-oauthlib/1.3.0/) | **`medusa`**, `python-twitter`, `trakt` | Module: `requests_oauthlib`
ext | `requests-toolbelt` | [0.9.1](https://pypi.org/project/requests-toolbelt/0.9.1/) | `cloudscraper` | Module: `requests_toolbelt`
**ext3** | `sgmllib3k` | [1.0.0](https://pypi.org/project/sgmllib3k/1.0.0/) | `feedparser` | File: `sgmllib.py`
ext | `six` | [1.15.0](https://pypi.org/project/six/1.15.0/) | **`medusa`**, `adba`, `configobj`, `html5lib`, `imdbpie`, `knowit`, `PyGithub`, `subliminal`, `tvdbapiv2`, `validators` | File: `six.py`
ext | **`soupsieve`** | [1.9.6](https://pypi.org/project/soupsieve/1.9.6/) | `beautifulsoup4` | -
ext | **`stevedore`** | [1.30.1](https://pypi.org/project/stevedore/1.30.1/) | `subliminal` | -
ext | **`subliminal`** | [2.1.0](https://pypi.org/project/subliminal/2.1.0/) | **`medusa`** | -
ext | **`tmdbsimple`** | [2.8.0](https://pypi.org/project/tmdbsimple/2.8.0/) | **`medusa`** | -
ext | **`tornado`** | [6.1](https://pypi.org/project/tornado/6.1/) | **`medusa`**, `tornroutes` | -
ext | **`tornroutes`** | [0.5.1](https://pypi.org/project/tornroutes/0.5.1/) | **`medusa`** | -
ext | **`trakt`** | [3.1.0](https://pypi.org/project/trakt/3.1.0/) | **`medusa`** | -
ext | `trans` | [2.1.0](https://pypi.org/project/trans/2.1.0/) | `imdbpie` | File: `trans.py`
ext | `ttl-cache` | [1.6](https://pypi.org/project/ttl-cache/1.6/) | **`medusa`**, `adba` | File: `ttl_cache.py`
ext | **`tvdbapiv2`** | pymedusa/[d6d0e9d](https://github.com/pymedusa/tvdbv2/tree/d6d0e9d98071c2d646beb997b336edbb0e98dfb7) | **`medusa`** | -
ext | **`urllib3`** | [1.24.1](https://pypi.org/project/urllib3/1.24.1/) | `requests` | -
ext | **`validators`** | [0.18.2](https://pypi.org/project/validators/0.18.2/) | **`medusa`** | -
ext | **`webencodings`** | [0.5.1](https://pypi.org/project/webencodings/0.5.1/) | `html5lib` | -
ext | **`wrapt`** | [1.10.11](https://pypi.org/project/wrapt/1.10.11/) | `deprecated` | -

#### Notes:
- `ext` compatible with Python 2 and Python 3
- `ext2` only compatible with Python 2
- `ext3` only compatible with Python 3
