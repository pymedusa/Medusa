# Automatic local file checks

The nightly Show Update checks local media inventories separately from metadata
updates. Continuing, unpaused shows receive daily file checks and retain their
usual metadata-update rules. Paused and ended shows receive a weekly local check
in batches distributed across all seven days. Manual full rescans retain their
existing behavior.

## Work performed

The first successful check builds an inventory of included show and season
folders, their direct media files, sizes, and modification times. Subsequent
checks read each known folder's identity and modification/change timestamps.
Only new or changed folders have their direct entries enumerated and media files
checked. Cached child folders are checked independently even when their parent
is unchanged, including previously empty folders.

If every folder is unchanged, the check performs no directory listings, individual
file checks, episode database queries, filename parsing, or inventory writes.
Folder metadata reads can still wake sleeping disks; this is reduced polling,
not a promise of zero disk access. No video contents are read or hashed. Hidden
directories, Extras, and directory symlinks are not traversed.

- Files in unchanged folders reuse their saved inventory. Their cached sizes
  cannot overwrite newer episode records saved by Medusa's importer.
- Freshly observed changes to known files update their saved file sizes.
- New or renamed files are parsed locally and matched only to existing episodes,
  including saved absolute, date, and scene numbering. Missing or ambiguous
  mappings remain unresolved for a manual rescan; the check never fetches them.
- Missing files in freshly checked folders follow the existing Skip Removed Files
  and deleted-status policy. Associated subtitle/metadata files and empty
  directories are left on disk.

The local path performs no indexer/XEM refresh, metadata generation, subtitle
refresh, media probing, or download scheduling. It uses the existing database
batch helper with conditional writes: a conflicting episode edit rolls back the
whole batch. Cached episode objects are invalidated only after commit.

Inventories reuse the existing application cache and survive application restarts.
The first check, a cleared cache, or an older inventory format requires one full
inventory. Existing paths and sizes avoid reparsing unchanged known files. A
successful manual full rescan or show removal clears the show's inventory entry.

## Detection limits

Directory timestamps track direct entry changes, rather than all changes within
files. Editing, truncating, or continuing to copy an existing file in place can
leave its parent folder unchanged. Restoring timestamps and filesystem timestamp
precision can also hide changes. Such changes require a manual full rescan or a
later change to that same folder. There is no automatic periodic file-by-file
audit. Medusa's own completed imports already save their episode records.

## Storage availability

An unreadable or interrupted inventory is incomplete, rather than evidence that
files were deleted. Changed storage identities, empty media inventories, and
disappeared recorded season directories preserve the existing records and require
storage verification or a manual full rescan. This includes intentional
whole-folder removal: automatic checking cannot reliably distinguish it from
unavailable storage. Folder fingerprints are rechecked before accepting a changed
inventory. No filesystem-metadata heuristic can prove that every remote mount is
available under every failure mode.

## Scheduling and logging

The configured nightly Show Update queues active shows every day. For each
paused or ended show, a stable hash of its indexer and series ID selects one
weekday. That weekday's batch is queued by the same nightly updater and is
immediately eligible to run. There is no additional delay spreading checks into
the daytime. Assignments survive restarts and do not depend on library order or
filesystem access. The distribution is approximate; it does not identify or
group physical storage volumes.

Only the current weekday's weekly batch is queued. Missed weekdays during downtime
wait for their next assigned weekday, avoiding a catch-up flood; a show can wait
up to a week after restart. Checks run one at a time at low queue priority; this
controls queue ordering, not operating-system CPU or I/O throttling. Pending
automatic passes must drain before another pass is queued. There is no hard
clock cutoff: a busy queue or a long-running batch can finish after nighttime.

Queued/running rescans are reused. A manual full rescan immediately upgrades a
pending local check or follows a running check. Full metadata updates and required
season-update rescans retain their existing behavior.
Successful checks log a compact summary of unchanged folders or reconciliation
results.

## Verification

`tests/test_local_files.py` exercises real filesystem inventories and SQLite
updates, with network requests and heavyweight episode construction forbidden.
It covers folder reuse, nested and empty folders, the in-place edit limitation,
shared files, renames, missing-file policies, local numbering, ambiguous matches,
unavailable storage, mount identity changes, and filesystem/database races.
`tests/test_db_conditional_batch.py` verifies the real batch helper's atomic
conflict rollback. The scheduler and queue tests cover weekly distribution,
nightly execution, overlap prevention, and immediate manual upgrades.
