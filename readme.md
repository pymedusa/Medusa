![medusa-name-logo-green-snakes](https://cloud.githubusercontent.com/assets/1867464/13375559/ede197ae-dd70-11e5-8cd0-b0eb239c977e.png)

[![Build Status](https://travis-ci.org/pymedusa/Medusa.svg?branch=develop)](https://travis-ci.org/pymedusa/Medusa) [![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/pymedusa/Medusa.svg)](http://isitmaintained.com/project/pymedusa/Medusa "Average time to resolve an issue") [![Percentage of issues still open](http://isitmaintained.com/badge/open/pymedusa/Medusa.svg)](http://isitmaintained.com/project/pymedusa/Medusa "Percentage of issues still open")  [![Codacy Badge](https://api.codacy.com/project/badge/Grade/ade58b4469dd4b38bbbd681913d97bfc)](https://www.codacy.com/app/pymedusa/Medusa?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pymedusa/Medusa&amp;utm_campaign=Badge_Grade)

=====
Automatic Video Library Manager for TV Shows. It watches for new episodes of your favorite shows, and when they are posted it does its magic.

#### Features
 - Manual search episodes (you choose what to snatch based on all kind of info: provider, seeds, release group)
 - Manual search for subtitles (useful when subtitle has low score because of typo in filename or alternative title)
 - Uses 'guessit' library to parse and enrich existing info (more precise than regexes)
 - Improved Anime shows support
 - Kodi/XBMC library updates, poster/banner/fanart downloads, and NFO/TBN generation
 - Sync your shows with Trakt. Keep shows/episode updated in Trakt watchlist 
 - Option to clean Kodi library when replacing existing files
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

#### Screenshots
- [Desktop (Full-HD)](http://imgur.com/a/4fpBk)
- [Mobile](http://imgur.com/a/WPyG6)

#### Dependencies
 To run Medusa from source you will need Python 2.7.10

#### [![Feature Requests](https://cloud.githubusercontent.com/assets/390379/10127973/045b3a96-6560-11e5-9b20-31a2032956b2.png)](https://github.com/pymedusa/Medusa/issues?q=is%3Aopen+is%3Aissue+label%3A%22Feature+Request%22)

##### [Medusa Issue Tracker](https://github.com/pymedusa/Medusa/issues)

##### [FAQ](https://github.com/pymedusa/Medusa/wiki/Frequently-Asked-Questions)

##### [Wiki](https://github.com/pymedusa/Medusa/wiki)

#### Important
Before using this with your existing database (sickbeard.db) please make a backup copy of it and delete any other database files such as cache.db and failed.db if present<br>
We HIGHLY recommend starting out with no database files at all to make this a fresh start but the choice is at your own risk.

#### Supported providers

A full list can be found here: [Link](https://github.com/pymedusa/Medusa/wiki/Medusa-Search-Providers)

#### Special Thanks to:
![image](https://rarbg.com/favicon.ico)[RARBG](https://rarbg.to)
![image](https://torrentproject.se/favicon.ico)[TorrentProject](https://torrentproject.se/about)
![image](https://thepiratebay.se/favicon.ico)[ThePirateBay](https://thepiratebay.se/)
![image](https://nzb.cat/favicon.ico)[NZB.cat](https://nzb.cat/)
![image](https://nzbgeek.info/favicon.ico)[NZBGeek](https://nzbgeek.info)
![image](https://raw.githubusercontent.com/pymedusa/Medusa/master/static/images/providers/dognzb.png)[DOGnzb](https://dognzb.cr)

#### Browsers support <sub><sub>made by <a href="https://godban.github.io">godban</a></sub></sub>

| [<img src="https://raw.githubusercontent.com/godban/browsers-support-badges/master/src/images/edge.png" alt="IE / Edge" width="16px" height="16px" />](http://godban.github.io/browsers-support-badges/)</br>IE / Edge | [<img src="https://raw.githubusercontent.com/godban/browsers-support-badges/master/src/images/firefox.png" alt="Firefox" width="16px" height="16px" />](http://godban.github.io/browsers-support-badges/)</br>Firefox | [<img src="https://raw.githubusercontent.com/godban/browsers-support-badges/master/src/images/chrome.png" alt="Chrome" width="16px" height="16px" />](http://godban.github.io/browsers-support-badges/)</br>Chrome | [<img src="https://raw.githubusercontent.com/godban/browsers-support-badges/master/src/images/safari.png" alt="Safari" width="16px" height="16px" />](http://godban.github.io/browsers-support-badges/)</br>Safari |
| --------- | --------- | --------- | --------- |
| Edge| last 2 versions| last 2 versions| last 2 versions

#### News and Changelog
[news.md and CHANGES.md have moved to a separate repo, click here](https://cdn.pymedusa.com)

#### External dependencies
This product uses [MediaInfo](http://mediaarea.net/MediaInfo) library, Copyright (c) 2002-2016 [MediaArea.net SARL](mailto:Info@MediaArea.net)

Binaries for Windows and MacOS are included. Linux distributions need to manually install MediaInfo.
MediaInfo is optional, but highly recommended since it increases the number of supported formats for video metadata extraction. Basic MKV metadata is supported when MediaInfo is not installed.
