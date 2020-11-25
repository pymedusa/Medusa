## 0.4.6 (25-11-2020)

Last version that runs on Python 2.7!

#### Improvements
- Vueified add existing shows ([8448](https://github.com/pymedusa/Medusa/pull/8448))
  - Get real time progress update on the shows adding
  - Add shows automatically when metadata is available
  - Preset show options
- Vueified add show ([8448](https://github.com/pymedusa/Medusa/pull/8448))
  - No more page redirects when you add a show that already exists
  - Select show list while adding show
  - Map show lists to anime, when configured in config -> anime
- Refactored scene exception methods ([8753](https://github.com/pymedusa/Medusa/pull/8753))

#### Fixes
- Fixed provider TVChaosUK ([8737](https://github.com/pymedusa/Medusa/pull/8737))

-----

## 0.4.5 (2020-11-13)

#### Fixes
- Updated EZTV provider URL
- Fixed email and prowl notifications

-----

## 0.4.4 (2020-11-04)

#### Improvements
- Replace unrar2 with rarfile
- Add EpisodeUpdater to scheduler
- Don't strip channel names so they are matched correctly
- Avoid exception when headers have no host

#### Fixes
- Fix notify lists for prowl and email ([8535](https://github.com/pymedusa/Medusa/pull/8535))
- Fix shows sorting by article sort using (the, a, an) was reversed in config-general ([8532](https://github.com/pymedusa/Medusa/pull/8532))
- Fix sending torrents to qBittorrent api version > 2.0.0 ([8528](https://github.com/pymedusa/Medusa/pull/8528))
- Fix decoding torrent hash from magnet links ([8563](https://github.com/pymedusa/Medusa/pull/8563))
- Fix provider AnimeBytes ([8609](https://github.com/pymedusa/Medusa/pull/8609))
- Fix provider Speedcd ([8609](https://github.com/pymedusa/Medusa/pull/8609))
- Fix season pack search, results not shown for multi-episode results ([8609](https://github.com/pymedusa/Medusa/pull/8609))
- Fix scene exceptions with year not being used
- Fix IPTorrents layout change
- Use b64decode instead of deprecated decodestring for basic auth

-----

## 0.4.3 (2020-09-08)

#### Improvements
- Updated all frontend libraries and dependencies

#### Fixes
- Fix no max season error when a show is incomplete ([8460](https://github.com/pymedusa/Medusa/pull/8460))
- Fix start error on some Python 2.7 builds

-----

## 0.4.2 (2020-09-06)

#### Improvements
- Added new page "restart", for restarting and shutting down Medusa ([8399](https://github.com/pymedusa/Medusa/pull/8399))
- Added new page "update", for updating Medusa to a new version ([8437](https://github.com/pymedusa/Medusa/pull/8437))

#### Fixes
- Fix show-selector using the show lists ([8426](https://github.com/pymedusa/Medusa/pull/8426))
- Fix home poster layout. Re-add the search by show title ([8415](https://github.com/pymedusa/Medusa/pull/8415))
- Fix backlog search ignoring cached search results ([8395](https://github.com/pymedusa/Medusa/pull/8395))
- Fix guessit parsing numbered episode titles as multi season ([8413](https://github.com/pymedusa/Medusa/pull/8413))
- Fix History page showing black text (on black) when using dark theme ([8375](https://github.com/pymedusa/Medusa/pull/8375))

-----

## 0.4.1 (2020-08-18)

#### Fixes
- Fixed show titles displayed in white text on the schedule page ([#8338](https://github.com/pymedusa/Medusa/pull/8338))
- Fixed Series show list title shown, also when it's the only show list used ([#8338](https://github.com/pymedusa/Medusa/pull/8338))
- Fixed home table layouts Downloads sorting ([#8338](https://github.com/pymedusa/Medusa/pull/8338))
- Fixed home table layouts previous and next episode sorting ([#8337](https://github.com/pymedusa/Medusa/pull/8337))
- Fixed show's show lists not stored after restart ([#8337](https://github.com/pymedusa/Medusa/pull/8337))

-----

## 0.4.0 (2020-08-15)

#### New Features
- Added Search shows by id ([#8308](https://github.com/pymedusa/Medusa/pull/8308))
- Added UI option to create your own show list categories ([#8308](https://github.com/pymedusa/Medusa/pull/8308))
- Add the ability to modify the Discord bot username ([#8148](https://github.com/pymedusa/Medusa/pull/8148))

#### Improvements
- Vueified Home page (Poster, small poster, banner, simple layouts) ([5345](https://github.com/pymedusa/Medusa/pull/5345))
- Vueified Snatch Selection page ([7345](https://github.com/pymedusa/Medusa/pull/7345))
- Add the save path option for qBittorrent version > 3.2 ([8304](https://github.com/pymedusa/Medusa/pull/8304))
- show-header: mark indexer used for adding show with star ([8286](https://github.com/pymedusa/Medusa/pull/8286))
- Utilize season search results from cache ([8281](https://github.com/pymedusa/Medusa/pull/8281))
- Improve season scene name handling for non-anime shows ([8155](https://github.com/pymedusa/Medusa/pull/8155))

#### Fixes
- Disable forcing of the scene option when adding shows ([8316](https://github.com/pymedusa/Medusa/pull/8316))
- Fix associated files matching more files than wanted ([8152](https://github.com/pymedusa/Medusa/pull/8152))

-----

## 0.3.16 (2020-04-27)

#### New Features
- Added Keep link as post processing method ([#7986](https://github.com/pymedusa/Medusa/pull/7986))
- Added EZTV as torrent provider ([#8004](https://github.com/pymedusa/Medusa/pull/8004))

#### Fixes
- Fixed PrivateHD and CinemaZ provider login ([#7991](https://github.com/pymedusa/Medusa/pull/7991))
- Fixed occasional subliminal exception ([#7989](https://github.com/pymedusa/Medusa/pull/7989))

-----

## 0.3.15 (2020-04-13)

#### Improvements
- Add show names with dashes to guessit expected titles ([#7918](https://github.com/pymedusa/Medusa/pull/7918))
- Provider YggTorrents: Add 'saison' as a season pack search keyword ([#7920](https://github.com/pymedusa/Medusa/pull/7920))
- Show Snatched or Downloaded release name when manually picking a subtitle ([#7955](https://github.com/pymedusa/Medusa/pull/7955))

#### Fixes
- Fixed root dirs not always shown on Home page ([#7921](https://github.com/pymedusa/Medusa/pull/7921))
- Fixed starting Medusa failed running Python 3.8 on Windows ([#7940](https://github.com/pymedusa/Medusa/pull/7940))
- Fixed Speed.cd provider login ([#7941](https://github.com/pymedusa/Medusa/pull/7941))
- Fixed [#7959](https://github.com/pymedusa/Medusa/issues/7959) - UI bug on schedule calendar view ([#7962](https://github.com/pymedusa/Medusa/pull/7962))
- Fixed running Scheduler with specific start time ([#7963](https://github.com/pymedusa/Medusa/pull/7963))

-----

## 0.3.14 (2020-03-30)

#### Improvements
- Search sub-folders for subtitles during post-processing

#### Fixes
- Fixed a bug that prevented the scheduler to run correctly

-----

## 0.3.13 (2020-03-28)

#### Improvements
- Improved show loading speed with lazy seasons loading
- Show specials are now always displayed at the bottom if enabled
- Added dynamic loading of providers
- Set scheduler last run after it has run
- Restricted scripts execution to Python scripts for security reasons (see [External scripts](https://github.com/pymedusa/Medusa/wiki/External-scripts))
- Added missing status handling in show header

#### Fixes
- Fixed indexer specific exceptions raising errors in show refresh ([#7837](https://github.com/pymedusa/Medusa/pull/7837))
- Replaced deprecated error.message syntax ([#7819](https://github.com/pymedusa/Medusa/pull/7819))
- Fixed saving of web root ([#7841](https://github.com/pymedusa/Medusa/pull/7841))
- Fixed authentication token returned as bytes ([#7842](https://github.com/pymedusa/Medusa/pull/7842))

-----

## 0.3.12 (2020-02-08)

#### Fixes
- Fixed guessit parser not using scene exceptions ([#7699](https://github.com/pymedusa/Medusa/pull/7699))
- Updated YggTorrent provider domain ([#7703](https://github.com/pymedusa/Medusa/pull/7703))

-----

## 0.3.11 (2020-01-31)

#### Improvements
- Updated Python and JavaScript dependencies
- Added a few new network icons

#### Fixes
- Fixed deluged move_torrent() when seed location is specified in the configuration ([#7586](https://github.com/pymedusa/Medusa/pull/7586))
- Fixed rare parser exception when anime episode doesn't exist ([#7613](https://github.com/pymedusa/Medusa/pull/7613))

-----

## 0.3.10 (2020-01-13)

#### New Features
- Added Opensubtitles VIP, aRGENTeaM and Subtitulamos subtitle providers ([#7555](https://github.com/pymedusa/Medusa/pull/7555), [#7518](https://github.com/pymedusa/Medusa/pull/7518))

#### Improvements
- Added `uniqueid` to Kodi 12+ show metadata ([#7483](https://github.com/pymedusa/Medusa/pull/7483))
- Updated AppLink to enable native mouse navigation ([#7498](https://github.com/pymedusa/Medusa/pull/7498))

#### Fixes
- Fixed Emby notifier error on Python 3 ([#7497](https://github.com/pymedusa/Medusa/pull/7497))
- Fixed more qBittorrent authentication bugs ([#7501](https://github.com/pymedusa/Medusa/pull/7501))
- Fixed `torrents.verifyCert` config patch ignored warning ([#7501](https://github.com/pymedusa/Medusa/pull/7501))
- Fixed dragging and saving Anime / Series list handles in Home - Poster layout ([#7502](https://github.com/pymedusa/Medusa/pull/7502))
- Fixed adding Anime with white/black listed release groups ([#7507](https://github.com/pymedusa/Medusa/pull/7507))
- Fixed Schedule page and Forced Search on Schedule page ([#7512](https://github.com/pymedusa/Medusa/pull/7512))
- Fixed manual search page release name bug ([#7517](https://github.com/pymedusa/Medusa/pull/7517))
- Fixed being unable to save post-processing config ([#7526](https://github.com/pymedusa/Medusa/pull/7526))
- Fixed qBittorrent error when torrent queueing is disabled ([#7541](https://github.com/pymedusa/Medusa/pull/7541))

-----

## 0.3.9 (2019-12-12)

#### Improvements
- Improved qBittorrent client ([#7474](https://github.com/pymedusa/Medusa/pull/7474))

#### Fixes
- Fixed season pack downloads occurring even if not needed ([#7472](https://github.com/pymedusa/Medusa/pull/7472))
- Fixed changing default indexer language and initial indexer in config-general ([#7478](https://github.com/pymedusa/Medusa/pull/7478))

-----

## 0.3.8 (2019-12-08)

#### Improvements
- Display Show: Display qualities in presets or allowed as green instead of yellow ([#7415](https://github.com/pymedusa/Medusa/pull/7415))
- Display Show: Add option to disable pagination ([#7438](https://github.com/pymedusa/Medusa/pull/7438))
- Improve a number of anime release names parsed by guessit ([#7418](https://github.com/pymedusa/Medusa/pull/7418)) ([#7396](https://github.com/pymedusa/Medusa/pull/7396)) ([#7427](https://github.com/pymedusa/Medusa/pull/7427))

#### Fixes
- Show Header: Fix showing correct amount of stars for the IMDB rating ([#7401](https://github.com/pymedusa/Medusa/pull/7401))
- Re-implement tvdb season poster/banners (was disabled because of tvdb api issues) ([#7460](https://github.com/pymedusa/Medusa/pull/7460))
- Fix showing the data directory in the bottom of some config pages ([#7424](https://github.com/pymedusa/Medusa/pull/7424))

-----

## 0.3.7 (2019-11-18)

#### Fixes
- Fixed broken TheTVDB caused by API v3 changes ([#7355](https://github.com/pymedusa/Medusa/pull/7355))
- DisplayShow: Fixed Xem and Medusa season exceptions not shown anymore ([#7360](https://github.com/pymedusa/Medusa/pull/7360))

-----

## 0.3.6 (2019-11-11)

#### New Features
- Added notifier for Discord (discordapp.com) ([#7189](https://github.com/pymedusa/Medusa/pull/7189))

#### Improvements
- Shows without any episodes can now be added ([#6977](https://github.com/pymedusa/Medusa/pull/6977))
- Vueified displayShow ([#6709](https://github.com/pymedusa/Medusa/pull/6709))
  - New subtitles search UI component
  - Direct toggle of show options on displayShow page like the checks for Subtitles, Season Folders, Paused, etc.
  - Mark episodes as "watched"
  - Added pagination
  - Added search field, that searches columns like Title, File and Episode number
- Added ability to use custom domain for TorrentDay provider ([#7326](https://github.com/pymedusa/Medusa/pull/7326))

#### Fixes
- Fixed AnimeBytes daily search, for multi-ep results ([#7190](https://github.com/pymedusa/Medusa/pull/7190))
- Fixed rare UnicodeDecodeError when parsing titles with Python 2.7 ([#7192](https://github.com/pymedusa/Medusa/pull/7192))
- Fixed displayShow loading of large shows with many seasons e.g. daily shows ([#6977](https://github.com/pymedusa/Medusa/pull/6977))
- Fixed torrent checker for client Transmission running on python 3 ([#7250](https://github.com/pymedusa/Medusa/pull/7250))
- Fixed provider beyond-hd due to added captcha and layout changes ([#7323](https://github.com/pymedusa/Medusa/pull/7323))
- Fixed provider bj-share due to layout changes ([#7250](https://github.com/pymedusa/Medusa/pull/7250))
- Fixed provider btdb due date format change in layout ([#7250](https://github.com/pymedusa/Medusa/pull/7250))
- Fixed exception when there is no anime XML ([#7256](https://github.com/pymedusa/Medusa/pull/7256))
- Fixed BTDB manual search & updated Xthor domain ([#7303](https://github.com/pymedusa/Medusa/pull/7303))
- Fixed duplicate manual search results for providers without unqiue URLs ([#7305](https://github.com/pymedusa/Medusa/pull/7305))
- Fixed exception when release groups aren't available for anime shows ([#7333](https://github.com/pymedusa/Medusa/pull/7333))

-----

## 0.3.5 (2019-09-08)

#### New Features
- Added multi-episode naming style with lowercase `e` ([#6910](https://github.com/pymedusa/Medusa/pull/6910))

#### Improvements
- Converted the footer to a Vue component ([#4520](https://github.com/pymedusa/Medusa/pull/4520))
- Converted Edit Show to a Vue SFC ([#4486](https://github.com/pymedusa/Medusa/pull/4486)
- Improved API v2 exception reporting on Python 2 ([#6931](https://github.com/pymedusa/Medusa/pull/6931))
- Added support for qBittorrent API v2. Required from qBittorrent version 4.2.0. ([#7040](https://github.com/pymedusa/Medusa/pull/7040))
- Removed the forced search queue item in favor of the backlog search queue item. ([#6718](https://github.com/pymedusa/Medusa/pull/6718))
- Show Header: Improved visibility of local and global configured required and ignored words. ([#7085](https://github.com/pymedusa/Medusa/pull/7085))
- Reduced frequency of file system access when not strictly required ([#7102](https://github.com/pymedusa/Medusa/pull/7102))

#### Fixes
- Fixed hdtorrent provider parse the publishing date with the day first ([#6847](https://github.com/pymedusa/Medusa/pull/6847))
- Fixed release link on Help & Info page ([#6854](https://github.com/pymedusa/Medusa/pull/6854))
- Fixed FreeMobile notifier message encode error ([#6867](https://github.com/pymedusa/Medusa/pull/6867))
- Fixed charset on API v2 responses with plain text content ([#6931](https://github.com/pymedusa/Medusa/pull/6931))
- Fixed logger causing an exception in certain cases ([#6932](https://github.com/pymedusa/Medusa/pull/6932))
- Fixed testing Plex media server when using multiple hosts ([#6976](https://github.com/pymedusa/Medusa/pull/6976))
- Fixed snatching for Xthor provider with Python 3 ([#7103](https://github.com/pymedusa/Medusa/pull/7103))

-----

## 0.3.4 (2019-06-13)

#### Fixes
- Fixed Jackett providers returning empty torrents on magnet redirect (2) ([#6827](https://github.com/pymedusa/Medusa/pull/6827))
- Fixed APIv2 exception when serializing allowed extensions to JSON ([#6835](https://github.com/pymedusa/Medusa/pull/6835))

-----

## 0.3.3 (2019-06-12)

#### New Features
- Added new provider Beyond-hd ([#6802](https://github.com/pymedusa/Medusa/pull/6802))

#### Fixes
- Fixed error when changing episode quality but not changing status ([#6784](https://github.com/pymedusa/Medusa/pull/6784))
- Fixed Jackett providers returning empty torrents on magnet redirect ([#6790](https://github.com/pymedusa/Medusa/pull/6790))
- Fixed error when using KnowIt with MediaInfo ([#6796](https://github.com/pymedusa/Medusa/pull/6796))

-----

## 0.3.2 (2019-06-05)

#### New Features
- Added nCore torrent provider ([#6537](https://github.com/pymedusa/Medusa/pull/6537))
- Added Gimmepeers torrent provider (credits to @mystycs) ([#6635](https://github.com/pymedusa/Medusa/pull/6635))
- Added BTDB torrent provider ([#6678](https://github.com/pymedusa/Medusa/pull/6678))

#### Improvements
- Converted the sub-menu into a Vue SFC ([#6724](https://github.com/pymedusa/Medusa/pull/6724))
- Converted View Log page into a Vue SFC ([#6738](https://github.com/pymedusa/Medusa/pull/6738))
- Converted the Quality Chooser into a Vue SFC ([#6737](https://github.com/pymedusa/Medusa/pull/6737))

#### Fixes
- Fixed lists not being saved when used with comma separated items ([#6428](https://github.com/pymedusa/Medusa/pull/6428))
- Fixed extra scripts running with Python 3 ([#6428](https://github.com/pymedusa/Medusa/pull/6428))
- Fixed Torrenting provider exception when offline ([#6430](https://github.com/pymedusa/Medusa/pull/6430))
- Fixed not displaying quality preferred in show-header when configured ([#6455](https://github.com/pymedusa/Medusa/pull/6455))
- Fixed snatching of air by date shows specials ([#6457](https://github.com/pymedusa/Medusa/pull/6457))
- Fixed email notifier name parser warning for ABD episodes ([#6527](https://github.com/pymedusa/Medusa/pull/6527))
- Fixed download of multi episode releases without single results ([#6537](https://github.com/pymedusa/Medusa/pull/6537))
- Fixed "send to trash" option not doing anything (Python 3.6 and higher) ([#6625](https://github.com/pymedusa/Medusa/pull/6625))
- Fixed setting episodes to archived in backlog overview ([#6636](https://github.com/pymedusa/Medusa/pull/6636))
- Fixed exception in Elite-Tracker provider when no result is found ([#6680](https://github.com/pymedusa/Medusa/pull/6680))
- Fixed exception in API v2 when an incorrect API key was provided, or none was provided ([#6703](https://github.com/pymedusa/Medusa/pull/6703))
- Removed legacy log-censoring code for Newznab providers ([#6705](https://github.com/pymedusa/Medusa/pull/6705))
- Fixed DelugeD remove torrents when ratio is reached (Python 2.7) ([#6702](https://github.com/pymedusa/Medusa/pull/6702))
- Fixed home page slow down issue ([#6754](https://github.com/pymedusa/Medusa/pull/6754))

## 0.3.1 (2019-03-20)

#### Fixes
- Fixed auto update causing DB issues ([#6356](https://github.com/pymedusa/Medusa/pull/6356))
- Fixed sending Kodi notifications (Python 3) ([#6355](https://github.com/pymedusa/Medusa/pull/6355))
- Fixed sending Slack notifications (Python 3) ([#6355](https://github.com/pymedusa/Medusa/pull/6355))
- Fixed possible error while getting AniDB scene exceptions (Python 3) ([#6355](https://github.com/pymedusa/Medusa/pull/6355))

-----

## 0.3.0 (2019-03-13)

#### New Features
- Added support for Python 3 (>= 3.5.0) ([#4982](https://github.com/pymedusa/Medusa/pull/4982))
- Added feature to search episodes early or late compared to their scheduled airdate ([#5874](https://github.com/pymedusa/Medusa/pull/5874))
- Added per show required/preferred words exclude option ([#6033](https://github.com/pymedusa/Medusa/pull/6033))

#### Improvements
- Vueified the partial mako template showheader.mako into show-header.vue ([#6189](https://github.com/pymedusa/Medusa/pull/6189))

#### Fixes
- Fixed saving newznab provider API key ([#5918](https://github.com/pymedusa/Medusa/pull/5918))
- Fixed permanent Docker update message ([#6018](https://github.com/pymedusa/Medusa/pull/6018))

-----

## 0.2.14 (2018-12-19)

#### New Features
- Added provider nordicbits ([#5854](https://github.com/pymedusa/Medusa/pull/5854))

#### Improvements
- Change the way we calculate and check the daily search interval for providers ([#5855](https://github.com/pymedusa/Medusa/issues/5855))
- During a backlog search, we searched for "any" cache result. And if the case, didn't attempt pulling new results from the provider. Now we search the provider when we didn't get any "candidates" from cache. ([#5816](https://github.com/pymedusa/Medusa/issues/5816))

#### Fixes
- Fixed double absolute numbers for anime shows where thexem sets an absolute which already exists ([#5801](https://github.com/pymedusa/Medusa/pull/5801))
- Fixed image cache not properly created from metadata for images other then posters ([#5810](https://github.com/pymedusa/Medusa/pull/5810))
- Fixed episode status comparison in subtitleMissedPP ([#5813](https://github.com/pymedusa/Medusa/pull/5813))
- Fixed anidex title parsing ([#5837](https://github.com/pymedusa/Medusa/pull/5837))
- Fixed (restore) the posibilty or configuring the default daily search search interval ([#5823](https://github.com/pymedusa/Medusa/pull/5823))
- Fixed notifications - kodi, 'allways on' config option ([#5871](https://github.com/pymedusa/Medusa/pull/5871))
- Fixed mis-mapped proper search interval config option of 24 hours, added 30 minutes ([#5896](https://github.com/pymedusa/Medusa/pull/5896))
- Fixed config - search settings, test nzb client connectivity ([#5897](https://github.com/pymedusa/Medusa/pull/5897))
- Fixed adding an episode to the my anidb list on post processing when enabled ([#5897](https://github.com/pymedusa/Medusa/pull/5897))
- Fixed creating banner and fanart from metadata. Any metadata images in the shows folder other then the poster, will now also become visible in Medusa ([#5808](https://github.com/pymedusa/Medusa/pull/5808))

-----

## 0.2.13 (2018-11-21)

#### Improvements
- Improved perfect match for subtitles downloading by making it a bit less strict ([#5729](https://github.com/pymedusa/Medusa/issues/5729))

#### Fixes
- Fixed ImportError when using Download Station client ([#5748](https://github.com/pymedusa/Medusa/pull/5748))
- Fixed Torrent Search path option not being saved ([#5736](https://github.com/pymedusa/Medusa/pull/5736))
- Fixed adding anime release group when adding show ([#5749](https://github.com/pymedusa/Medusa/pull/5749))
- Fixed Pushover debug log causing BraceException ([#5759](https://github.com/pymedusa/Medusa/pull/5759))
- Fixed torrent method Downloadstation not selected after restart ([#5761](https://github.com/pymedusa/Medusa/pull/5761))
- Fixed changing show location, should now also utilise the option 'CREATE_MISSING_SHOW_DIRS' ([#5795](https://github.com/pymedusa/Medusa/pull/5795))

-----

## 0.2.12 (2018-11-16)

#### New Features
- Added Join notifier ([#5241](https://github.com/pymedusa/Medusa/pull/5241))

#### Improvements
- Vueified "config - notifications" page:
  - Improved components: config-textbox, select-list, show-selector, config-textbox-number
  - Improved responsiveness of the notification page on smaller screens ([#4913](https://github.com/pymedusa/Medusa/pull/4913))
- Allowed the use of priorities in the Pushover notifier ([#5567](https://github.com/pymedusa/Medusa/pull/5567))
- Added delete method to EpisodeHandler (apiv2), for deleting a single episode ([#5685](https://github.com/pymedusa/Medusa/pull/5685))
- Allowed Nyaa and Anidex to search for non-anime shows ([#5680](https://github.com/pymedusa/Medusa/pull/5680) & [#5681](https://github.com/pymedusa/Medusa/pull/5681))
- Do not allow to enable the anime options, when using tmdb or tvmaze ([#5701](https://github.com/pymedusa/Medusa/pull/5701))
- Vueified "config - search" page. Improved responsiveness of the notification page on smaller screens. ([#5553](https://github.com/pymedusa/Medusa/pull/5553))

#### Fixes
- Fixed test not working for Download Station ([#5561](https://github.com/pymedusa/Medusa/pull/5561))
- Fixed wrong placeholder reference in log ([#5562](https://github.com/pymedusa/Medusa/pull/5562))
- Fixed guessit exception when parsing release without title ([#5569](https://github.com/pymedusa/Medusa/pull/5569))
- Fixed Download Station BraceAdapter exception ([#5573](https://github.com/pymedusa/Medusa/pull/5573))
- Fixed saving multiple metadata providers ([#5576](https://github.com/pymedusa/Medusa/pull/5576))
- Fixed show-selector for libraries with more than 1k shows ([#5623](https://github.com/pymedusa/Medusa/pull/5623))
- Fixed Growl registration error ([#5684](https://github.com/pymedusa/Medusa/pull/5684))

-----

## 0.2.11 (2018-10-29)

#### Improvements
- Updated `guessit` to version 3.0.0 ([#4244](https://github.com/pymedusa/Medusa/pull/4244))
- Updated the API v2 endpoint to handle concurrent requests ([#4970](https://github.com/pymedusa/Medusa/pull/4970))
- Converted some of the show header to Vue ([#5087](https://github.com/pymedusa/Medusa/pull/5087))
- Converted "Add Show" options into a Vue SFC ([#4848](https://github.com/pymedusa/Medusa/pull/4848))
- Added publishing date to Speed.CD provider ([#5190](https://github.com/pymedusa/Medusa/pull/5190))
- Converted the "quality pill" into a Vue SFC ([#5103](https://github.com/pymedusa/Medusa/pull/5103))
- Vueified restart page, moved JS files to Vue, added `state-switch` component and misc changes ([#5159](https://github.com/pymedusa/Medusa/pull/5159))
- Added support for SABnzbd's Direct Unpack feature ([#5385](https://github.com/pymedusa/Medusa/pull/5385))
- Added config/search values to apiv2 ([#5079](https://github.com/pymedusa/Medusa/pull/5079))
- Improved the add new show page responsiveness on smaller width viewports ([#5509](https://github.com/pymedusa/Medusa/pull/5509))

#### Fixes
- Fixed many release name parsing issues as a result of updating `guessit` ([#4244](https://github.com/pymedusa/Medusa/pull/4244))
- Fixed Speed.CD provider exception during searches ([#5190](https://github.com/pymedusa/Medusa/pull/5190))
- Fixed adba lib trowing exceptions getting release groups for some anime shows ([#5125](https://github.com/pymedusa/Medusa/pull/5125))
- Fixed trakt icon not showing on the displayShow page, when a trakt id is available ([#5300](https://github.com/pymedusa/Medusa/pull/5300))
- Fixed editShow page crashing because of a memory overflow ([#5314](https://github.com/pymedusa/Medusa/pull/5314))
- Fixed exception when downloading missed subtitles ([#5356](https://github.com/pymedusa/Medusa/pull/5356))
- Fixed popularShows path on router ([#5356](https://github.com/pymedusa/Medusa/pull/5356))
- Fixed imdbpie exception on connection error ([#5386](https://github.com/pymedusa/Medusa/pull/5386))
- Fixed metadata settings not being saved ([#5385](https://github.com/pymedusa/Medusa/pull/5385))
- Fixed Synology DS missing location and wrong icon ([#5443](https://github.com/pymedusa/Medusa/pull/5443))
- Fixed saving "config - postprocessing frequency" value ([#5482](https://github.com/pymedusa/Medusa/pull/5482))
- Fixed database trying to update even if up to date ([#5543](https://github.com/pymedusa/Medusa/pull/5543))

-----

## 0.2.10 (2018-09-09)

#### Fixes
- Fixed error due to `null` values in the episodes database table ([#5132](https://github.com/pymedusa/Medusa/pull/5132))
- Fixed extraneous calls to AniDB when navigating to any show's page ([#5166](https://github.com/pymedusa/Medusa/pull/5166))
- Fixed being unable to start Medusa due to an import error ([#5145](https://github.com/pymedusa/Medusa/pull/5145))
- Fixed UI bugs on:
  - Home page (when using "split home in tabs") ([#5126](https://github.com/pymedusa/Medusa/pull/5126))
  - Status page ([#5127](https://github.com/pymedusa/Medusa/pull/5127))
  - Preview Rename page ([#5169](https://github.com/pymedusa/Medusa/pull/5169))
  - Post Processing Config page - saving `select-list` values incorrectly ([#5165](https://github.com/pymedusa/Medusa/pull/5165))
- Fixed bug in TorrentLeech provider when fetching multiple pages of results ([#5172](https://github.com/pymedusa/Medusa/pull/5172))

-----

## 0.2.9 (2018-09-06)

#### Improvements
- Converted Post-Processing Config to a Vue SFC ([#4259](https://github.com/pymedusa/Medusa/pull/4259) + [#4946](https://github.com/pymedusa/Medusa/pull/4946))
- Bundled the web application using Webpack ([#4692](https://github.com/pymedusa/Medusa/pull/4692))
- Updated adba (anidb) client to version 1.0.0 (python 2/3 compatible) ([#4822](https://github.com/pymedusa/Medusa/pull/4822))
- Changed caching location for the adba and simpleanidb libs to the default Medusa cache location ([#4822](https://github.com/pymedusa/Medusa/pull/4822))
- Added a new field name 'watched' to the tv_episodes db table. UI will be added in future ([#4825](https://github.com/pymedusa/Medusa/pull/4825))
- Standardized most titles and headers ([#4663](https://github.com/pymedusa/Medusa/pull/4663))
- Converted IRC page into a Vue SFC ([#5089](https://github.com/pymedusa/Medusa/pull/5089))

#### Fixes
- Fixed error when changing episode status from episode status management ([#4783](https://github.com/pymedusa/Medusa/pull/4783))
- Fixed multi-episode snatches not being marked as snatched in history ([#229](https://github.com/pymedusa/Medusa/issues/229))
- Fixed whole seasons being downloaded as multi-episode replacement ([#4750](https://github.com/pymedusa/Medusa/issues/4750))
- Fixed yggtorrent changed url to new url ([#4843](https://github.com/pymedusa/Medusa/issues/4843))
- Fixed excessive anidb udp calls when opening editShow ([#4822](https://github.com/pymedusa/Medusa/pull/4822))
- Fixed UI not loading using edge browser, when using a reverse proxy (without an alternative port) ([#4928](https://github.com/pymedusa/Medusa/pull/4928))
- Fixed episode lookup with conflicting show IDs ([#4933](https://github.com/pymedusa/Medusa/pull/4933))
- Fixed error getting season scene exceptions on show page [#4964](https://github.com/pymedusa/Medusa/pull/4964)
- Fixed testing email notification with TLS ([#4972](https://github.com/pymedusa/Medusa/pull/4972))
- Fixed provider hd-space parsing pubdate like 'yesterday at 12:00:00' ([#5111](https://github.com/pymedusa/Medusa/pull/5111))
- Fixed apiv2 call hanging, when opening an anime show, that has malformed data on anidb (with anidb enabled) ([#4961](https://github.com/pymedusa/Medusa/pull/4961))

-----

## 0.2.8 (2018-07-28)

#### Fixes
- Fixed tabs on home page when using the split home layout ([#4764](https://github.com/pymedusa/Medusa/pull/4764))
- Fixed black screen after update ([#4774](https://github.com/pymedusa/Medusa/pull/4774))
- Fixed error when trying to rename episodes ([#4774](https://github.com/pymedusa/Medusa/pull/4774))

-----

## 0.2.7 (2018-07-27)

#### New Features
- Hot-swap themes: No need to restart Medusa after changing the theme ([#4271](https://github.com/pymedusa/Medusa/pull/4271))

#### Improvements
- Moved the following routes to use `VueRouter` + `http-vue-loader`:
  - `/config` - Help & Info ([#4374](https://github.com/pymedusa/Medusa/pull/4374))
  - `/addShows` - Add Shows ([#4564](https://github.com/pymedusa/Medusa/pull/4564))
  - `/addRecommended` - Add Recommended Shows ([#4564](https://github.com/pymedusa/Medusa/pull/4564))
  - `/login` - Login ([#4634](https://github.com/pymedusa/Medusa/pull/4634))
- Removed the old `/ui` route ([#4565](https://github.com/pymedusa/Medusa/pull/4565))
- Added a simple "Loading..." message while the page is loading ([#4629](https://github.com/pymedusa/Medusa/pull/4629))
- Expanded episode status management capabilities, added support for Downloaded, Archived ([#4647](https://github.com/pymedusa/Medusa/pull/4647))
- Added ability to manually change episode quality ([#4658](https://github.com/pymedusa/Medusa/pull/4658))
- Converted to Vue components:
  - header ([#4519](https://github.com/pymedusa/Medusa/pull/4519))
  - sub-menu ([#4739](https://github.com/pymedusa/Medusa/pull/4739))
- Add Viaplay network logo ([#4691](https://github.com/pymedusa/Medusa/pull/4691))
- Convert Vue components to SFC - Single-File Components ([#4696](https://github.com/pymedusa/Medusa/pull/4696))

#### Fixes
- Fixed malformed non-ASCII characters displaying for Windows users on "View Logs" page ([#4492](https://github.com/pymedusa/Medusa/pull/4492))
- Fixed Emby test notification ([#4622](https://github.com/pymedusa/Medusa/pull/4622))
- Fixed NorBits provider formatting download URL incorrectly ([#4642](https://github.com/pymedusa/Medusa/pull/4642))
- Fixed reference linking ([#4463](https://github.com/pymedusa/Medusa/pull/4463))
- Fixed the Show Selector not honoring user option to split shows & anime ([#4625](https://github.com/pymedusa/Medusa/pull/4625))
- Fixed unhandled request error on Add Existing Show ([#4639](https://github.com/pymedusa/Medusa/pull/4639))
- Fixed Telegram & Growl message encoding ([#4657](https://github.com/pymedusa/Medusa/pull/4657))
- Fixed being unable to change scene numbering for first 2 episodes of each season on displayShow ([#4656](https://github.com/pymedusa/Medusa/pull/4656))
- Fixed YggTorrents provider downloads by updating the provider's URL ([#4725](https://github.com/pymedusa/Medusa/pull/4725))
- Fixed Abnormal provider login check ([#4727](https://github.com/pymedusa/Medusa/pull/4727))
- Fixed IMDB cache location ([#4745](https://github.com/pymedusa/Medusa/pull/4745))
- Fixed "Edit Show" page sometimes failing to load the show ([#4756](https://github.com/pymedusa/Medusa/pull/4756))

-----

### [**Previous versions**](https://github.com/pymedusa/medusa.github.io/blob/master/news/CHANGES.md#v026)
