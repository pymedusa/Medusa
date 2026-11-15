# coding=utf-8
"""Reconcile a show's media inventory using local records and filesystem metadata only."""

import logging
import os
from collections import Counter, defaultdict

from medusa import app, db, helpers, ws
from medusa.cache import cache
from medusa.common import ARCHIVED, DOWNLOADED, IGNORED, Quality, SKIPPED, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, WANTED
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.rules import default_api

log = BraceAdapter(logging.getLogger(__name__))


def normalized_path(path):
    """Use one absolute path spelling for filesystem and stored episode locations."""
    return os.path.normcase(os.path.abspath(path))


def _directory_fingerprint(directory):
    """Identify storage and direct entry changes without opening individual files."""
    metadata = os.stat(directory)
    return (metadata.st_dev, metadata.st_ino, metadata.st_mtime_ns, metadata.st_ctime_ns)


def _read_media_directory(directory):
    """Read direct entries only; the caller decides which child folders need scanning."""
    files = {}
    children = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name.startswith('.') or entry.name == 'Extras':
                continue

            if entry.is_dir(follow_symlinks=False):
                children.append(normalized_path(entry.path))
            elif helpers.is_media_file(entry.name) and entry.is_file():
                metadata = entry.stat()
                files[normalized_path(entry.path)] = (metadata.st_size, metadata.st_mtime_ns)

    return files, tuple(sorted(children))


def scan_media_files(root, previous=None):
    """Return files, folder snapshots, and the folders whose entries were read.

    An unchanged folder reuses its direct file fingerprints and child names. Its
    children are still checked: a season's timestamp does not propagate to the
    show folder. First use (including an old cache format) reads every folder.
    Directory symlinks are not followed. Any read failure rejects the inventory.
    """
    previous = previous or {}
    old_directories = previous.get('directories', {}) if previous.get('version') == 2 else {}
    old_files = previous.get('files', {})
    inventory = {}
    directories = {}
    rescanned = set()
    pending = [root]

    while pending:
        directory = pending.pop()
        fingerprint = _directory_fingerprint(directory)
        cached = old_directories.get(directory)
        if cached and fingerprint[:2] != cached['fingerprint'][:2]:
            raise OSError('Media directory storage identity changed: {0}'.format(directory))

        if cached and fingerprint == cached['fingerprint']:
            children = cached['children']
            directories[directory] = cached
        else:
            files, children = _read_media_directory(directory)
            inventory.update(files)
            rescanned.add(directory)
            directories[directory] = {
                'fingerprint': fingerprint,
                'children': children,
                'files': tuple(sorted(files)),
            }

        pending.extend(children)

    if not rescanned:
        return old_files, directories, rescanned

    for directory, snapshot in directories.items():
        if directory not in rescanned:
            inventory.update((path, old_files[path]) for path in snapshot['files'])

    return inventory, directories, rescanned


def _inventory_key(series):
    return 'local-files:v1:{0}:{1}:{2}'.format(series.indexer, series.series_id, normalized_path(series.location))


def invalidate_local_file_inventory(series):
    """Forget fingerprints after a full rescan or removal of the show."""
    cache.delete(_inventory_key(series))


def _inside_root(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def _directory_identities(root, paths):
    """Keep a disappearing season folder or changed mount from looking like deleted files."""
    directories = {root}
    for path in paths:
        directory = os.path.dirname(path)
        while _inside_root(directory, root):
            directories.add(directory)
            if directory == root:
                break
            directory = os.path.dirname(directory)

    identities = {}
    for directory in directories:
        metadata = os.stat(directory)
        identities[directory] = (metadata.st_dev, metadata.st_ino)
    return identities


def _matching_rows(guess, rows, scene_rows, is_anime, is_scene):
    """Resolve all parsed numbers against saved episodes; ambiguity leaves the file untouched."""
    if guess.get('date'):
        candidates = [row for row in rows if row['airdate'] == guess['date'].toordinal()]
        return candidates if len(candidates) == 1 else []

    season = guess.get('season')
    numbers = guess.get('episode', [])
    if not isinstance(numbers, list):
        numbers = [numbers]
    if isinstance(season, list) or not numbers:
        return []

    matches = []
    for number in numbers:
        candidates = []
        if is_scene:
            if season is None and is_anime:
                mappings = [row for row in scene_rows if row['scene_absolute_number'] == number]
            else:
                mappings = [row for row in scene_rows if (row['scene_season'], row['scene_episode']) == (season, number)]
            coordinates = {(row['season'], row['episode']) for row in mappings}
            candidates = [row for row in rows if (row['season'], row['episode']) in coordinates]
            if not candidates:
                if season is None and is_anime:
                    candidates = [row for row in rows if row['scene_absolute_number'] == number and number > 0]
                else:
                    candidates = [row for row in rows if (row['scene_season'], row['scene_episode']) == (season, number)]

        if not candidates:
            if season is None and is_anime:
                candidates = [row for row in rows if row['absolute_number'] == number]
            elif season is not None:
                candidates = [row for row in rows if (row['season'], row['episode']) == (season, number)]

        if len(candidates) != 1:
            return []
        matches.extend(candidates)

    return matches


def _new_file_changes(series, path, fingerprint, rows, scene_rows, inventory):
    guess = default_api.guessit(os.path.basename(path), options={
        'type': 'episode',
        'implicit': True,
        'episode_prefer_number': bool(series.is_anime),
        'expected_title': [series.name],
    })
    targets = _matching_rows(guess, rows, scene_rows, series.is_anime, series.is_scene)

    # Multiple files for one episode require a deliberate choice, not overwrite order.
    if not targets or any(row['location'] and normalized_path(row['location']) in inventory for row in targets):
        return []

    changes = []
    for row in targets:
        downloaded = row['status'] in (SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, DOWNLOADED)
        downloaded = downloaded or (row['status'] in (WANTED, SKIPPED) and not row['location'])
        values = {
            'location': path,
            'file_size': fingerprint[0],
            'status': DOWNLOADED if downloaded else ARCHIVED,
            'quality': Quality.from_guessit(guess),
            'release_name': os.path.splitext(os.path.basename(path))[0],
            'release_group': guess.get('release_group') or '',
        }
        changes.append((row, values))

    return changes


def _removed_file_values(row):
    values = {
        'location': '', 'file_size': 0, 'hasnfo': False, 'hastbn': False,
        'release_name': '', 'release_group': '', 'is_proper': False,
        'version': 0, 'manually_searched': False,
    }
    if row['status'] in (ARCHIVED, DOWNLOADED, IGNORED, SKIPPED):
        values.update(status=app.EP_DEFAULT_DELETED_STATUS, subtitles='',
                      subtitles_searchcount=0, subtitles_lastsearch='')
    return values


def _write_changes(connection, series, changes):
    queries = []
    for row, values in changes:
        cached = series.episodes.get(row['season'], {}).get(row['episode'])
        if cached is not None and cached.dirty:
            return False

        assignments = ', '.join('{0} = ?'.format(column) for column in values)
        queries.append([
            'UPDATE tv_episodes SET ' + assignments +
            ' WHERE indexer = ? AND showid = ? AND season = ? AND episode = ? AND location = ? AND file_size = ?'
            ' AND status = ? AND quality = ?',
            list(values.values()) + [
                series.indexer, series.series_id, row['season'], row['episode'],
                row['location'], row['file_size'], row['status'], row['quality'],
            ],
        ])

    try:
        results = connection.mass_action(queries, expected_rowcount=1)
    except db.StaleRecordError:
        return False
    if len(results) != len(changes):
        return False

    # Do not construct Episode objects here: loading their scene numbers may fetch XEM.
    for row, _ in changes:
        series.episodes.get(row['season'], {}).pop(row['episode'], None)
    ws.Message('showUpdated', series.to_json()).push()
    return True


def reconcile_local_files(series):
    """Update existing episode file records without fetching metadata or changing files.

    Unchanged known files need no parsing or episode writes. Unrecognized additions
    remain for manual review. Empty/inaccessible inventories and changed filesystem
    identities preserve records, because disconnected storage can resemble deletion.
    Folder timestamps gate file enumeration. The existing application cache keeps
    inventories across restarts. In-place edits inside unchanged folders require
    a manual full rescan; cached file sizes must never overwrite newer DB records.
    """
    root = normalized_path(series.location)
    key = _inventory_key(series)
    previous = cache.get(key, ignore_expiration=True)
    previous = previous if isinstance(previous, dict) else {}

    try:
        metadata = os.stat(root)
        identity = (metadata.st_dev, metadata.st_ino)
        if previous and previous['identity'] != identity:
            log.warning('Local file check skipped for {show}: storage identity changed.', {'show': series.name})
            return False
        inventory, directory_snapshots, rescanned = scan_media_files(root, previous)
    except OSError as error:
        log.warning('Local file check incomplete for {show}: {error}', {'show': series.name, 'error': error})
        return False

    if not rescanned:
        log.info('Local file check for {show}: {folders} folders unchanged; no individual files checked.',
                 {'show': series.name, 'folders': len(directory_snapshots)})
        return True

    connection = db.DBConnection()
    rows = connection.select(
        'SELECT season, episode, location, file_size, status, quality, absolute_number, airdate, '
        'scene_season, scene_episode, scene_absolute_number FROM tv_episodes WHERE indexer = ? AND showid = ?',
        [series.indexer, series.series_id])
    by_path = defaultdict(list)
    for row in rows:
        if row['location']:
            by_path[normalized_path(row['location'])].append(row)

    if by_path and not inventory:
        log.warning('Local file check skipped for {show}: no media found; verify storage or rescan manually.', {'show': series.name})
        return False

    try:
        directories = _directory_identities(root, set(inventory) | set(by_path))
        if previous.get('version') != 2:
            for directory, old_identity in previous.get('directories', {}).items():
                if directory in directories and directories[directory] != old_identity:
                    log.warning('Local file check skipped for {show}: a media directory changed storage.', {'show': series.name})
                    return False
    except OSError:
        return False

    old_files = previous.get('files', {})
    changes = []
    new_paths = []
    for path, fingerprint in inventory.items():
        if os.path.dirname(path) not in rescanned:
            continue

        known = by_path.get(path, [])
        same_size = known and all(row['file_size'] == fingerprint[0] for row in known)
        if same_size and (path not in old_files or old_files[path] == fingerprint):
            continue

        if known:
            changes.extend((row, {'file_size': fingerprint[0]}) for row in known)
        elif old_files.get(path) != fingerprint:
            new_paths.append(path)

    scene_rows = []
    if new_paths and series.is_scene:
        scene_rows = connection.select(
            'SELECT season, episode, scene_season, scene_episode, scene_absolute_number '
            'FROM scene_numbering WHERE indexer = ? AND indexer_id = ?', [series.indexer, series.series_id])

    additions = []
    for path in sorted(new_paths):
        additions.extend(_new_file_changes(series, path, inventory[path], rows, scene_rows, inventory))
    ownership = Counter((row['season'], row['episode']) for row, _ in additions)
    ambiguous_paths = {values['location'] for row, values in additions if ownership[(row['season'], row['episode'])] != 1}
    additions = [(row, values) for row, values in additions if values['location'] not in ambiguous_paths]
    changes.extend(additions)
    reassigned = {(row['season'], row['episode']) for row, _ in additions}

    missing = [path for path in by_path if path not in inventory and _inside_root(path, root)
               and os.path.dirname(path) in rescanned]
    if not app.SKIP_REMOVED_FILES:
        for path in missing:
            for row in by_path[path]:
                if (row['season'], row['episode']) not in reassigned:
                    changes.append((row, _removed_file_values(row)))

    # A file may disappear or finish copying during enumeration. Reject that pass
    # before recording missing files or accepting the new fingerprint baseline.
    try:
        current = os.stat(root)
        if (current.st_dev, current.st_ino) != identity:
            return False
        if _directory_identities(root, set(inventory) | set(by_path)) != directories:
            return False
        for directory, snapshot in directory_snapshots.items():
            if _directory_fingerprint(directory) != snapshot['fingerprint']:
                return False
        for path in missing:
            try:
                os.stat(path)
            except FileNotFoundError:
                continue
            return False
        for row, values in changes:
            path = normalized_path(values.get('location') or row['location'])
            if path in inventory:
                current = os.stat(path)
                if (current.st_size, current.st_mtime_ns) != inventory[path]:
                    return False
    except OSError:
        return False

    if changes and not _write_changes(connection, series, changes):
        return False

    snapshot = {'version': 2, 'identity': identity, 'files': inventory, 'directories': directory_snapshots}
    if snapshot != previous:
        cache.set(key, snapshot)
    log.info('Local file check for {show}: {folders} folders scanned, {files} media files, '
             '{changed} episode records changed, {unresolved} unresolved additions.',
             {'show': series.name, 'folders': len(rescanned), 'files': len(inventory), 'changed': len(changes),
              'unresolved': len(new_paths) - len({values['location'] for _, values in additions})})
    return True
