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
- Added per show required/preferred words exclude option ([#4982](https://github.com/pymedusa/Medusa/pull/6033))

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
