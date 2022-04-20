# coding=utf-8
"""Request handler for series assets."""
from __future__ import unicode_literals

import logging
from os import mkdir, path

from medusa import app, helpers
from medusa.common import Quality, qualityPresets, statusStrings
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantUpdateShowException,
)
from medusa.logger.adapters.style import CustomBraceAdapter
from medusa.scene_numbering import xem_refresh
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier

from tornado.escape import json_decode

log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SeriesMassEdit(BaseRequestHandler):
    """Series mass edit operation request handler."""

    #: resource name
    name = 'massedit'
    #: identifier
    identifier = None
    #: allowed HTTP methods
    allowed_methods = ('POST', )

    def post(self):
        """Perform a mass update action."""
        required_options = (
            'paused', 'defaultEpisodeStatus', 'anime', 'sports', 'scene',
            'airByDate', 'seasonFolders', 'subtitles', 'qualities', 'language', 'languageKeep'
        )
        data = json_decode(self.request.body)
        shows = data.get('shows', [])
        options = data.get('options')
        errors = 0

        if not options:
            return self._bad_request('Options missing')

        missing_options = []
        for req_option in required_options:
            if req_option not in options:
                missing_options.append(req_option)

        if missing_options:
            return self._bad_request(f"Missing options: {', '.join(missing_options)}")

        paused = options.get('paused')
        default_ep_status = options.get('defaultEpisodeStatus')
        if isinstance(default_ep_status, str):
            default_ep_status = {v: k for k, v in statusStrings.items()}.get(default_ep_status)
        anime = options.get('anime')
        sports = options.get('sports')
        scene = options.get('scene')
        air_by_date = options.get('airByDate')
        dvd_order = options.get('dvdOrder')
        season_folders = options.get('seasonFolders')
        subtitles = options.get('subtitles')
        qualities = options.get('qualities')
        language = options.get('language')
        language_keep = options.get('languageKeep')

        for show_slug in shows:
            identifier = SeriesIdentifier.from_slug(show_slug)
            show_obj = Series.find_by_identifier(identifier)

            if not show_obj:
                continue

            cur_root_dir = path.dirname(show_obj._location)
            cur_show_dir = path.basename(show_obj._location)
            for root_dir in options.get('rootDirs'):
                if cur_root_dir != root_dir['old']:
                    continue

                if root_dir['old'] != root_dir['new']:
                    new_show_dir = path.join(root_dir['new'], cur_show_dir)
                    log.info('For show {show_name} changing dir from {old_location} to {new_location}', {
                             'show_name': show_obj.name, 'old_location': show_obj._location, 'new_location': new_show_dir})
                else:
                    new_show_dir = show_obj._location

            new_paused = show_obj.paused if paused is None else paused
            new_default_ep_status = show_obj.default_ep_status if default_ep_status is None else default_ep_status
            new_anime = show_obj.anime if anime is None else anime
            new_sports = show_obj.sports if sports is None else sports
            new_scene = show_obj.scene if scene is None else scene
            new_air_by_date = show_obj.air_by_date if air_by_date is None else air_by_date
            new_dvd_order = show_obj.dvd_order if dvd_order is None else dvd_order
            new_season_folders = show_obj.season_folders if season_folders is None else season_folders
            new_subtitles = show_obj.subtitles if subtitles is None else subtitles
            new_language = show_obj.lang if language_keep else language

            # If both are false (two empty arrays), use the shows current value.
            if not qualities['allowed'] and not qualities['preferred']:
                new_quality_allowed, new_quality_preferred = show_obj.current_qualities
            else:
                new_quality_allowed, new_quality_preferred = qualities['allowed'], qualities['preferred']

            # If user set quality_preset remove all preferred_qualities
            if Quality.combine_qualities(new_quality_allowed, new_quality_preferred) in qualityPresets:
                new_quality_preferred = []

            errors += self.mass_edit_show(
                show_obj, location=new_show_dir,
                allowed_qualities=new_quality_allowed, preferred_qualities=new_quality_preferred,
                season_folders=new_season_folders, paused=new_paused, air_by_date=new_air_by_date, sports=new_sports,
                dvd_order=new_dvd_order, subtitles=new_subtitles, anime=new_anime, scene=new_scene,
                default_ep_status=new_default_ep_status, language=new_language
            )

        return self._created(data={'errors': errors})

    def mass_edit_show(
        self, show_obj, location=None, allowed_qualities=None, preferred_qualities=None,
        season_folders=None, paused=None, air_by_date=None, sports=None, dvd_order=None, subtitles=None,
        anime=None, scene=None, default_ep_status=None, language=None
    ):
        """Variation of the original `editShow`, where `directCall` is always true."""
        allowed_qualities = allowed_qualities or []
        preferred_qualities = preferred_qualities or []

        errors = 0

        do_update_scene_numbering = not (scene == show_obj.scene and anime == show_obj.anime)

        if not isinstance(allowed_qualities, list):
            allowed_qualities = [allowed_qualities]

        if not isinstance(preferred_qualities, list):
            preferred_qualities = [preferred_qualities]

        with show_obj.lock:
            new_quality = Quality.combine_qualities([int(q) for q in allowed_qualities],
                                                    [int(q) for q in preferred_qualities])
            show_obj.quality = new_quality

            # reversed for now
            if bool(show_obj.season_folders) != bool(season_folders):
                show_obj.season_folders = season_folders
                try:
                    app.show_queue_scheduler.action.refreshShow(show_obj)
                except CantRefreshShowException as error:
                    errors += 1
                    log.warning("Unable to refresh show '{show}': {error}", {
                        'show': show_obj.name, 'error': error
                    })

            # Check if we should erase parsed cached results for that show
            do_erase_parsed_cache = False
            for item in [('scene', scene), ('anime', anime), ('sports', sports),
                         ('air_by_date', air_by_date), ('dvd_order', dvd_order)]:
                if getattr(show_obj, item[0]) != item[1]:
                    do_erase_parsed_cache = True
                    # Break if at least one setting was changed
                    break

            show_obj.paused = paused
            show_obj.scene = scene
            show_obj.anime = anime
            show_obj.sports = sports
            show_obj.subtitles = subtitles
            show_obj.air_by_date = air_by_date
            show_obj.default_ep_status = int(default_ep_status)
            show_obj.dvd_order = dvd_order
            show_obj.lang = language

            # if we change location clear the db of episodes, change it, write to db, and rescan
            old_location = path.normpath(show_obj._location)
            new_location = path.normpath(location)
            if old_location != new_location:
                changed_location = True
                log.info('Changing show location to: {new}', {'new': new_location})
                if not path.isdir(new_location):
                    if app.CREATE_MISSING_SHOW_DIRS:
                        log.info("Show directory doesn't exist, creating it")
                        try:
                            mkdir(new_location)
                        except OSError as error:
                            errors += 1
                            changed_location = False
                            log.warning("Unable to create the show directory '{location}'. Error: {msg}", {
                                        'location': new_location, 'msg': error})
                        else:
                            log.info('New show directory created')
                            helpers.chmod_as_parent(new_location)
                    else:
                        changed_location = False
                        log.warning("New location '{location}' does not exist. "
                                    "Enable setting 'Create missing show dirs'", {'location': location})

                # Save new location to DB only if we changed it
                if changed_location:
                    show_obj.location = new_location

                if changed_location and path.isdir(new_location):
                    try:
                        app.show_queue_scheduler.action.refreshShow(show_obj)
                    except CantRefreshShowException as error:
                        errors += 1
                        log.warning("Unable to refresh show '{show}'. Error: {error}", {
                                    'show': show_obj.name, 'error': error})

            # Save all settings changed while in show_obj.lock
            show_obj.save_to_db()

        if do_update_scene_numbering or do_erase_parsed_cache:
            try:
                xem_refresh(show_obj)
            except CantUpdateShowException as error:
                errors += 1
                log.warning("Unable to update scene numbering for show '{show}': {error}",
                            {'show': show_obj.name, 'error': error})

            # Must erase cached DB results when toggling scene numbering
            show_obj.erase_provider_cache()

            # Erase parsed cached names as we are changing scene numbering
            show_obj.flush_episodes()
            show_obj.erase_cached_parse()

            # Need to refresh show as we updated scene numbering or changed show format
            try:
                app.show_queue_scheduler.action.refreshShow(show_obj)
            except CantRefreshShowException as error:
                errors += 1
                log.warning(
                    "Unable to refresh show '{show}'. Please manually trigger a full show refresh. "
                    'Error: {error!r}'.format(show=show_obj.name, error=error),
                    {'show': show_obj.name, 'error': error}
                )

        return errors
