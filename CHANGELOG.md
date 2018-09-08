## Unreleased

#### New Features

#### Improvements
- Updated `guessit` to version 3.0.0 ([#4244](https://github.com/pymedusa/Medusa/pull/4244))
- Updated the API v2 endpoint to handle concurrent requests ([#4970](https://github.com/pymedusa/Medusa/pull/4970))

#### Fixes
- Fixed many release name parsing issues as a result of updating `guessit` ([#4244](https://github.com/pymedusa/Medusa/pull/4244))
- Fixed UI bugs in home page (when using "split home in tabs") and status page ([#5126](https://github.com/pymedusa/Medusa/pull/5126) + [#5127](https://github.com/pymedusa/Medusa/pull/5127))

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
