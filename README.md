# Medusa

<p align="center">
  <img src=".github/assets/medusa-logo.png" alt="Medusa logo">
</p>

<p align="center">
  <a href="https://github.com/pymedusa/Medusa/actions/workflows/python-backend.yml?query=branch%3Adevelop">
    <img src="https://github.com/pymedusa/Medusa/actions/workflows/python-backend.yml/badge.svg?branch=develop" alt="Backend tests">
  </a>
  <a href="https://github.com/pymedusa/Medusa/actions/workflows/node-frontend.yml?query=branch%3Adevelop">
    <img src="https://github.com/pymedusa/Medusa/actions/workflows/node-frontend.yml/badge.svg?branch=develop" alt="Frontend tests">
  </a>
  <a href="https://github.com/pymedusa/Medusa/actions/workflows/api-tests.yml?query=branch%3Adevelop">
    <img src="https://github.com/pymedusa/Medusa/actions/workflows/api-tests.yml/badge.svg?branch=develop" alt="API tests">
  </a>
  <br>
  <a href="https://github.com/sindresorhus/xo">
    <img src="https://img.shields.io/badge/code_style-XO-5ed9c7.svg" alt="XO code style">
  </a>
  <a href="https://codecov.io/gh/pymedusa/Medusa">
    <img src="https://codecov.io/gh/pymedusa/Medusa/branch/develop/graph/badge.svg" alt="Codecov">
  </a>
</p>

Medusa is a self-hosted automatic video library manager for TV shows. It monitors configured shows, searches supported Usenet and torrent providers, sends releases to configured download clients, and organizes completed episodes with configurable metadata, subtitles, and post-processing.

**On this page:** [Features](#features) · [Installation](#installation) · [Updating](#updating) · [Support](#documentation-and-support) · [Security](#security) · [Contributing](#contributing)

**Project links:** [Wiki](https://github.com/pymedusa/Medusa/wiki) · [FAQ](https://github.com/pymedusa/Medusa/wiki/FAQ%27s-and-Fixes) · [Issues](https://github.com/pymedusa/Medusa/issues) · [GitHub Discussions](https://github.com/pymedusa/Medusa/discussions) · [Discord](https://discord.gg/zMdAdUK) · [Reddit](https://www.reddit.com/r/PyMedusa/) · [Changelog](CHANGELOG.md)

## How it works

Medusa retrieves show metadata from the selected indexer, searches configured
torrent and Usenet providers, sends the selected release to an external download
client, and then renames, organizes, enriches, and notifies your media library.

Metadata indexer → Search provider → Download client → Post-processing → Media server (Kodi, Plex, and Emby)

> [!NOTE]
> Medusa requires external torrent or Usenet providers and a compatible download
> client. It does not provide media or access to provider services.
>
> Use Medusa only with services and content that you are authorized to access.

## Features

### Search and downloads

- Automatic scheduled torrent and Usenet searches, including backlog, proper, and repack searches.
- Manual episode and season-pack searches with detailed selectable results. Users can compare provider, quality, release group, seeders, peers, and publication information before snatching.
- Torrent client integrations include Deluge, Synology Download Station, MLDonkey, qBittorrent, rTorrent, Transmission, and uTorrent.
- NZB integrations include SABnzbd and NZBGet, with black-hole and RSS-based workflows. NZBGet duplicate handling supports DupeKey and DupeScore.
- Configurable download clients, failed-download tracking, and retry support.
- Support for specials, season packs, and multi-episode releases.
- Provider caching and processed-result tracking reduce repeated parsing of previously seen releases.

### Metadata and episode management

- Metadata support through TVDBv2, TVmaze, TMDB, and IMDb, with external identifier mappings and integrations for services such as AniDB, Trakt, and AniList.
- Per-show indexer selection and the ability to change an existing show indexer.
- Posters, banners, fanart, NFO, and thumbnail metadata generation.
- Trakt watchlist import and collection synchronization.
- Air-date and DVD ordering support.
- XEM scene numbering and mappings.
- Bulk episode status management and views for missing, wanted, quality-upgrade, and upcoming episodes.

### Parsing, anime, and subtitles

- Release-name parsing and enrichment using GuessIt, including anime-specific parsing.
- AniDB integration for anime-related mappings and metadata workflows.
- Anime release-group white- and blacklists.
- Automatic subtitle matching and downloading.
- Manual subtitle search with provider, language, score, and matching details when automatic selection is not suitable.
- Optional delay of post-processing until required subtitles are available.

### Post-processing and library integration

- Configurable renaming and sorting with copy, move, hardlink, and symlink processing methods.
- Additional post-processing script support.
- Cleanup of associated files and empty directories during replacement and post-processing.
- Interactive explanations for Allowed and Preferred quality profiles.
- Preview of how quality changes affect backlog size.
- Kodi, Plex, and Emby library updates, plus optional Kodi library cleanup when replacing existing media.
- Per-season metadata updates when supported by the selected indexer, with automatic full-show fallback.

### Notifications and integrations

Notifications through Kodi, Plex, Emby, Discord, Slack, Telegram, email, Trakt, Pushbullet, Pushover, and other supported services.

## Installation

Docker is the recommended installation method for most server and NAS deployments. Source installation remains useful for developers and unsupported platforms.

| Method | Recommended for | Notes |
| --- | --- | --- |
| Docker | Most server and NAS installations | Recommended for most users |
| From source | Developers and unsupported platforms | Requires Python 3.9 or later |
| Windows setup | Windows users | Source quick start below and platform-specific wiki guidance |
| Community packages | Synology, QNAP, Asustor, and other NAS platforms | Maintained outside the main Medusa repository |

<table>
  <tr>
    <td align="center" width="50%">
      <a href="#docker">
        <img src=".github/assets/icons/docker.svg" width="48" height="48" alt="Docker">
        <br>
        <strong>Docker</strong>
      </a>
      <br>
      <sub>Recommended for most server and NAS deployments.</sub>
    </td>
    <td align="center" width="50%">
      <a href="#from-source">
        <img src=".github/assets/icons/python.svg" width="48" height="48" alt="Python">
        <br>
        <strong>From source</strong>
      </a>
      <br>
      <sub>For developers and platforms without a maintained package.</sub>
    </td>
  </tr>
</table>

### Docker

The official image is [`pymedusa/medusa`](https://hub.docker.com/r/pymedusa/medusa) on Docker Hub. It is built from this repository and published for `linux/amd64`, `linux/arm/v7`, and `linux/arm64`.

| Tag | Branch | Use |
| --- | --- | --- |
| `latest` | `master` | Stable installations |
| `master` | `master` | Stable installations |
| `develop` | `develop` | Recent changes; may be less stable |

The container listens on port `8081` and uses these volumes:

| Volume | Purpose |
| --- | --- |
| `/config` | Medusa configuration and database |
| `/downloads` | Download location |
| `/tv` | TV show library |
| `/anime` | Anime library |

Environment variables:

| Variable | Purpose |
| --- | --- |
| `PUID` | User ID for file permissions |
| `PGID` | Group ID for file permissions |
| `TZ` | Optional timezone (for example `Etc/UTC`) |

Minimal Docker Compose example:

```yaml
services:
  medusa:
    image: pymedusa/medusa:latest
    container_name: medusa
    ports:
      - "8081:8081"
    environment:
      PUID: "1000"
      PGID: "1000"
      TZ: "Etc/UTC"
    volumes:
      - ./config:/config
      - ./downloads:/downloads
      - ./tv:/tv
      - ./anime:/anime
    restart: unless-stopped
```

A community-maintained alternative is available from [LinuxServer.io](https://hub.docker.com/r/linuxserver/medusa) (`lscr.io/linuxserver/medusa`). It currently publishes `amd64` and `arm64` images.

### From source

Python 3.9 or later is required. Python 3.9 through 3.13 is currently tested in CI.

You also need Git. [MediaInfo](https://mediaarea.net/en/MediaInfo) is recommended for richer video metadata extraction. UnRAR (or a compatible RAR extractor) is recommended when processing archived downloads. Using a virtual environment is strongly recommended.

Linux/macOS quick start:

```bash
git clone --branch master --single-branch https://github.com/pymedusa/Medusa.git
cd Medusa

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python start.py
```

Open <http://localhost:8081> after startup.

Use the `develop` branch only for testing unreleased changes.

On Windows, create and activate a virtual environment with `py -m venv .venv` and `.venv\Scripts\Activate.ps1` before installing requirements. A minimal equivalent setup is:

```powershell
git clone --branch master --single-branch https://github.com/pymedusa/Medusa.git
cd Medusa

py -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python start.py
```

A systemd service template is available in [`runscripts/init.systemd`](runscripts/init.systemd) for Linux installations.

### Other platforms and community packages

Platform-specific installers and NAS packages may be maintained by community projects. Check their documentation and maintenance status before installing.

- Windows setup guidance: [Installation and configuration guides](https://github.com/pymedusa/Medusa/wiki/Installation-&-Configuration-Guides)
- NAS and community packages (including Synology, QNAP, Asustor): [Installation and configuration guides](https://github.com/pymedusa/Medusa/wiki/Installation-&-Configuration-Guides)

### Detailed installation guides

Use the wiki for detailed installation instructions, Windows setup, Linux service setup, NAS packages, upgrades, migrations, reverse proxy setups, and troubleshooting.

Some older platform-specific wiki pages may require updates. Verify package and dependency versions before following legacy instructions.

## Release channels

| Channel | Branch or image tag | Intended use |
| --- | --- | --- |
| Stable | `master` / `latest` | Normal installations |
| Development | `develop` | Testing recent changes |

The Docker `develop` tag tracks recent changes from the `develop` branch and may be less stable than `latest`.

## Updating

- Docker users should pull the selected image tag and recreate the container.
- Source installations should back up their configuration before updating the Git checkout.
- Users tracking `develop` should expect unreleased changes.

## Documentation and support

- [Wiki](https://github.com/pymedusa/Medusa/wiki)
- [Installation and configuration guides](https://github.com/pymedusa/Medusa/wiki/Installation-&-Configuration-Guides)
- [FAQ](https://github.com/pymedusa/Medusa/wiki/FAQ%27s-and-Fixes)
- [Supported providers](https://github.com/pymedusa/Medusa/wiki/Medusa-Search-Providers)
- [Using Jackett with Medusa](https://github.com/pymedusa/Medusa/wiki/Using-Jackett-with-Medusa)
- Use the [issue tracker](https://github.com/pymedusa/Medusa/issues) for reproducible bugs.
- Use the filtered [feature request list](https://github.com/pymedusa/Medusa/issues?q=is%3Aopen+is%3Aissue+label%3A%22Feature+Request%22) to review or propose enhancements.
- Use [GitHub Discussions](https://github.com/pymedusa/Medusa/discussions), [Discord](https://discord.gg/zMdAdUK), or the [PyMedusa subreddit](https://www.reddit.com/r/PyMedusa/) for usage questions and community discussion.
- [Changelog](CHANGELOG.md) and [GitHub Releases](https://github.com/pymedusa/Medusa/releases)

<table>
  <tr>
    <td align="center" width="50%">
      <a href="https://discord.gg/zMdAdUK">
        <img src=".github/assets/icons/discord.svg" width="40" height="40" alt="Discord">
        <br>
        <strong>Discord</strong>
      </a>
      <br>
      <sub>Real-time community discussion and user help.</sub>
    </td>
    <td align="center" width="50%">
      <a href="https://www.reddit.com/r/PyMedusa/">
        <img src=".github/assets/icons/reddit.svg" width="40" height="40" alt="Reddit">
        <br>
        <strong>Reddit community</strong>
      </a>
      <br>
      <sub>Browse community questions, discussions, and shared experience.</sub>
    </td>
  </tr>
</table>

## Backup and upgrades

Back up the complete configuration directory and all database files before upgrading, changing branches, testing a development build, or migrating from another application. Follow the relevant migration documentation before modifying or deleting database files.

Users migrating from SickBeard or SickRage can find guidance in the [installation guide](https://github.com/pymedusa/Medusa/wiki/Installation-&-Configuration-Guides).

## Security

Please report security vulnerabilities through [GitHub's private vulnerability reporting](https://github.com/pymedusa/Medusa/security/advisories/new). Do not disclose sensitive vulnerability details in a public issue.

## Contributing

Contributions are welcome. Create a focused branch from the appropriate upstream branch and read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Please follow the [Code of Conduct](code-of-conduct.md).

Developer resources include the source-controlled [API v2 contract](dredd/api-description.yml).

## License

Medusa is licensed under the GNU General Public License v3.0. See [COPYING.txt](COPYING.txt).

## Acknowledgements

[LinuxServer.io](https://www.linuxserver.io) maintains a community Docker image for Medusa.

Service icons are sourced from [Simple Icons](https://simpleicons.org/) and are used only to identify their respective services.

Medusa can use [MediaInfo](https://mediaarea.net/en/MediaInfo) to improve video metadata extraction. MediaInfo is optional for source installations and is included in the official Docker image.
