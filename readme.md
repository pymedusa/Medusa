<p align="center">
  <img src="https://cdn.rawgit.com/pymedusa/medusa.github.io/4360d494/images/logo/new-logo.png"/>
</p>
<p align="center" title="Build Status">
  <a href="https://travis-ci.com/github/pymedusa/Medusa">
    <img src="https://api.travis-ci.com/pymedusa/Medusa.svg?branch=develop" alt=""/>
  </a>
  <a href="http://isitmaintained.com/project/pymedusa/Medusa" title="Average time to resolve an issue">
    <img src="http://isitmaintained.com/badge/resolution/pymedusa/Medusa.svg" alt="Average time to resolve an issue"/>
  </a>
  <a href="http://isitmaintained.com/project/pymedusa/Medusa" title="Percentage of issues still open">
    <img src="http://isitmaintained.com/badge/open/pymedusa/Medusa.svg" alt="Percentage of issues still open"/>
  </a>
  <br>
  <a href="https://codebeat.co/projects/github-com-pymedusa-medusa-develop" title="">
    <img src="https://codebeat.co/badges/4b801428-c8b3-47aa-83aa-1d82677c52c0" alt="codebeat badge"/>
  </a>
  <a href="https://github.com/sindresorhus/xo" title="">
    <img src="https://img.shields.io/badge/code_style-XO-5ed9c7.svg" alt="XO code style"/>
  </a>
  <a href="https://codecov.io/gh/pymedusa/Medusa" title="">
    <img src="https://codecov.io/gh/pymedusa/Medusa/branch/develop/graph/badge.svg" alt="codecov"/>
  </a>
</p>


### Automatic Video Library Manager for TV Shows. It watches for new episodes of your favorite shows, and when they are posted it does its magic.

#### Exclusive features
 - Supports TVMaze and TMDB indexers
 - Manual search episodes (you choose what to snatch based on all kind of info: provider, seeds, release group)
 - Manual search for subtitles (useful when subtitle has low score because of typo in filename or alternative title)
 - Support for Python 3
 - Uses 'guessit' library to parse and enrich existing info (more precise than regexes)
 - Improved Anime shows support
 - Faster DailySearcher|Backlog|Find propers as we only process new items. Already processed items are discarded.
 - Option to clean Kodi library when replacing existing files
 - Better quality explanations and consistent quality code in all threads
 - See on the fly if your backlogged episodes will be increased/reduced while changing qualities
 - Postpone Post Processing until Medusa downloads wanted subtitle (useful to only show media if subtitle available)
 - Clean up any leftover files/folders if media file is deleted
 - Nightly showupdater updates only the season of the show, which has been updated by the indexer, for tvdb and tmdb.

 #### Features
 - Kodi/XBMC library updates, poster/banner/fanart downloads, and NFO/TBN generation
 - Sync your shows with Trakt. Keep shows/episode updated in Trakt watchlist
 - Configurable automatic episode renaming, sorting, and other processing
 - Easily see what episodes you're missing, are airing soon, and more
 - Automatic torrent/nzb searching, downloading, and processing at the qualities you want
 - Largest list of supported torrent and nzb providers, both public and private
 - Can notify Kodi, XBMC, Growl, Trakt, Twitter, and more when new episodes are available
 - Searches TheTVDB.com and AniDB.net for shows, seasons, episodes, and metadata
 - Episode status management allows for mass failing seasons/episodes to force retrying
 - DVD Order numbering for returning the results in DVD order instead of Air-By-Date order
 - Allows you to choose which indexer to have Medusa search its show info from when importing
 - Automatic XEM Scene Numbering/Naming for seasons/episodes
 - Available for any platform, uses a simple HTTP interface
 - Specials and multi-episode torrent/nzb support
 - Automatic subtitles matching and downloading
 - Improved failed download handling
 - DupeKey/DupeScore for NZBGet 12+
 - Real SSL certificate validation

#### Dependencies
 To run Medusa from source you will need one of these Python versions:
 * **Python 3** – 3.6.0 and newer

#### Installation - direct
 Start [here](https://github.com/pymedusa/Medusa/wiki/Installation-&-Configuration-Guides) to read the installation guides for different setups.

#### Installation - Docker
 There's a direct build available on [Dockerhub](https://hub.docker.com/r/pymedusa/medusa/) which is updated directly from this repo on every commit to master.

 For alternate architectures, the [linuxserver.io](https://www.linuxserver.io) team have kindly produced docker images for X86, armhf and aarch64 platforms. This is built from an older intermediary Dockerfile.

* X86 - [Dockerhub](https://hub.docker.com/r/linuxserver/medusa/), [Github](https://github.com/linuxserver/docker-medusa)
* armhf - [Dockerhub](https://hub.docker.com/r/lsioarmhf/medusa/), [Github](https://github.com/linuxserver/docker-medusa-armhf)
* aarch64 - [Dockerhub](https://hub.docker.com/r/lsioarmhf/medusa-aarch64/), [Github](https://github.com/linuxserver/docker-medusa-arm64)

#### [![Feature Requests](https://cloud.githubusercontent.com/assets/390379/10127973/045b3a96-6560-11e5-9b20-31a2032956b2.png)](https://github.com/pymedusa/Medusa/issues?q=is%3Aopen+is%3Aissue+label%3A%22Feature+Request%22)

##### [Medusa Issue Tracker](https://github.com/pymedusa/Medusa/issues)

##### [FAQ](https://github.com/pymedusa/Medusa/wiki/Frequently-Asked-Questions)

##### [Wiki](https://github.com/pymedusa/Medusa/wiki)

##### [Discord](https://discord.gg/zMdAdUK)

#### Important
Before using this with your existing database (sickbeard.db) please make a backup copy of it and delete any other database files such as cache.db and failed.db if present<br>
We HIGHLY recommend starting out with no database files at all to make this a fresh start but the choice is at your own risk.

#### Supported providers

A partial list can be found [here](https://github.com/pymedusa/Medusa/wiki/Medusa-Search-Providers). Jackett is supported, however it must be configured [as follows](https://github.com/pymedusa/Medusa/wiki/Using-Jackett-with-Medusa).

#### Special Thanks to:
![RARBG](https://rarbg.com/favicon.ico) [RARBG](https://rarbg.to)
&nbsp;&middot;&nbsp;
![NZB.cat](https://nzb.cat/favicon.ico) [NZB.cat](https://nzb.cat/)
&nbsp;&middot;&nbsp;
![NZBGeek](https://nzbgeek.info/favicon.ico) [NZBGeek](https://nzbgeek.info)
&nbsp;&middot;&nbsp;
![DOGnzb](https://raw.githubusercontent.com/pymedusa/Medusa/master/themes-default/slim/static/images/providers/dognzb.png) [DOGnzb](https://dognzb.cr)
&nbsp;&middot;&nbsp;
![DanishBits](https://raw.githubusercontent.com/pymedusa/Medusa/master/themes-default/slim/static/images/providers/danishbits.png) [DanishBits](https://danishbits.org)

#### Browsers support <sub><sub>made by <a href="https://godban.github.io">godban</a></sub></sub>

| [<img src="https://raw.githubusercontent.com/godban/browsers-support-badges/master/src/images/edge.png" alt="IE / Edge" width="16px" height="16px" />](http://godban.github.io/browsers-support-badges/)</br>IE / Edge | [<img src="https://raw.githubusercontent.com/godban/browsers-support-badges/master/src/images/firefox.png" alt="Firefox" width="16px" height="16px" />](http://godban.github.io/browsers-support-badges/)</br>Firefox | [<img src="https://raw.githubusercontent.com/godban/browsers-support-badges/master/src/images/chrome.png" alt="Chrome" width="16px" height="16px" />](http://godban.github.io/browsers-support-badges/)</br>Chrome | [<img src="https://raw.githubusercontent.com/godban/browsers-support-badges/master/src/images/safari.png" alt="Safari" width="16px" height="16px" />](http://godban.github.io/browsers-support-badges/)</br>Safari |
| --------- | --------- | --------- | --------- |
| Edge| last 2 versions| last 2 versions| last 2 versions

#### News and Changelog
[news.md has moved to a separate repo, click here](https://github.com/pymedusa/medusa.github.io/blob/master/news/news.md)

[The changelog can be found here](https://github.com/pymedusa/Medusa/blob/develop/CHANGELOG.md)
[The changelog for versions prior to v0.2.7 can be found here](https://github.com/pymedusa/medusa.github.io/blob/master/news/CHANGES.md)

#### External dependencies
This product uses [MediaInfo](http://mediaarea.net/MediaInfo) library, Copyright (c) 2002-2016 [MediaArea.net SARL](mailto:Info@MediaArea.net)

Binaries for Windows and MacOS are included. Linux distributions need to manually install MediaInfo.
MediaInfo is optional, but highly recommended since it increases the number of supported formats for video metadata extraction. Basic MKV metadata is supported when MediaInfo is not installed.
