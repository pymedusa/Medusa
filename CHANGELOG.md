## Unreleased

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
