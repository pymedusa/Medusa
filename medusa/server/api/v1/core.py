# coding=utf-8
# Author: Dennis Lutter <lad1337@gmail.com>
# Author: Jonathon Saine <thezoggy@gmail.com>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

# TODO: break this up into separate files
# pylint: disable=line-too-long,too-many-lines,abstract-method
# pylint: disable=no-member,method-hidden,missing-docstring,invalid-name
from __future__ import unicode_literals

import json
import logging
import os
import sys
import time
from collections import OrderedDict
from datetime import date, datetime

from medusa import (
    app,
    classes,
    db,
    helpers,
    image_cache,
    network_timezones,
    sbdatetime,
    subtitles,
    ui,
)
from medusa.common import (
    ARCHIVED,
    DOWNLOADED,
    FAILED,
    IGNORED,
    Overview,
    Quality,
    SKIPPED,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    UNAIRED,
    UNSET,
    WANTED,
    statusStrings,
)
from medusa.helper.common import (
    dateFormat,
    dateTimeFormat,
    pretty_file_size,
    sanitize_filename,
    timeFormat,
    try_int,
)
from medusa.helper.exceptions import CantUpdateShowException, ShowDirectoryNotFoundException
from medusa.helpers.quality import get_quality_string
from medusa.indexers.api import indexerApi
from medusa.indexers.config import INDEXER_TMDB, INDEXER_TVDBV2, INDEXER_TVMAZE
from medusa.indexers.exceptions import IndexerError, IndexerShowNotFound
from medusa.logger import LOGGING_LEVELS, filter_logline, read_loglines
from medusa.logger.adapters.style import BraceAdapter
from medusa.media.banner import ShowBanner
from medusa.media.fan_art import ShowFanArt
from medusa.media.network_logo import ShowNetworkLogo
from medusa.media.poster import ShowPoster
from medusa.search.queue import BacklogQueueItem
from medusa.show.coming_episodes import ComingEpisodes
from medusa.show.history import History
from medusa.show.show import Show
from medusa.system.restart import Restart
from medusa.system.shutdown import Shutdown
from medusa.updater.version_checker import CheckVersion

from requests.compat import unquote_plus

from six import binary_type, iteritems, itervalues, string_types, text_type, viewitems

from tornado.web import RequestHandler


if sys.version_info[0] == 2:
    from future import standard_library
    standard_library.install_aliases()

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

INDEXER_IDS = {
    0: 'indexerid',
    INDEXER_TVDBV2: 'tvdbid',
    INDEXER_TVMAZE: 'tvmazeid',
    INDEXER_TMDB: 'tmdbid'
}

# basically everything except RESULT_SUCCESS / success is bad
RESULT_SUCCESS = 10  # only use inside the run methods
RESULT_FAILURE = 20  # only use inside the run methods
RESULT_TIMEOUT = 30  # not used yet :(
RESULT_ERROR = 40  # only use outside of the run methods !
RESULT_FATAL = 50  # only use in Api.default() ! this is the "we encountered an internal error" error
RESULT_DENIED = 60  # only use in Api.default() ! this is the access denied error

result_type_map = {
    RESULT_DENIED: 'denied',
    RESULT_ERROR: 'error',
    RESULT_FATAL: 'fatal',
    RESULT_FAILURE: 'failure',
    RESULT_SUCCESS: 'success',
    RESULT_TIMEOUT: 'timeout',
}


class ApiHandler(RequestHandler):
    """Api class that returns json results."""

    version = 7  # use an int since float-point is unpredictable

    def __init__(self, *args, **kwargs):
        super(ApiHandler, self).__init__(*args, **kwargs)

    # def set_default_headers(self):
    #     self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')

    def get(self, *args, **kwargs):
        kwargs = {k: self.get_arguments(k) for k in self.request.arguments}
        for arg, value in iteritems(kwargs):
            if len(value) == 1:
                kwargs[arg] = value[0]

        args = args[1:]

        # set the output callback
        # default json
        output_callback_dict = {
            'default': self._out_as_json,
            'image': self._out_as_image,
        }

        access_msg = u'API :: {0} - gave correct API KEY. ACCESS GRANTED'.format(self.request.remote_ip)
        log.debug(access_msg)

        # set the original call_dispatcher as the local _call_dispatcher
        _call_dispatcher = self.call_dispatcher
        # if profile was set wrap "_call_dispatcher" in the profile function
        if 'profile' in kwargs:
            from profilehooks import profile

            _call_dispatcher = profile(_call_dispatcher, immediate=True)
            del kwargs['profile']

        try:
            out_dict = _call_dispatcher(args, kwargs)
        except Exception as error:  # real internal error oohhh nooo :(
            log.exception(u'API :: {0!r}', error)
            error_data = {
                'error_msg': text_type(error),
                'args': args,
                'kwargs': kwargs
            }
            out_dict = _responds(RESULT_FATAL, error_data,
                                 'Medusa encountered an internal error! Please report to the Devs')

        if 'outputType' in out_dict:
            output_callback = output_callback_dict[out_dict['outputType']]
        else:
            output_callback = output_callback_dict['default']

        try:
            self.finish(output_callback(out_dict))
        except Exception:
            pass

    def _out_as_image(self, _dict):
        self.set_header('Content-Type', _dict['image'].media_type)
        return _dict['image'].media

    def _out_as_json(self, _dict):
        self.set_header('Content-Type', 'application/json;charset=UTF-8')
        try:
            out = json.dumps(_dict, ensure_ascii=False, sort_keys=True)
            callback = self.get_query_argument('callback', None) or self.get_query_argument('jsonp', None)
            if callback:
                out = '{0}({1});'.format(callback, out)  # wrap with JSONP call if requested
        except Exception as error:  # if we fail to generate the output fake an error
            log.exception(u'API :: Traceback')
            out = '{{"result": "{0}", "message": "error while composing output: {1!r}"}}'.format(
                result_type_map[RESULT_ERROR], error
            )
        return out

    def call_dispatcher(self, args, kwargs):  # pylint:disable=too-many-branches
        """ calls the appropriate CMD class
            looks for a cmd in args and kwargs
            or calls the TVDBShorthandWrapper when the first args element is a number
            or returns an error that there is no such cmd
        """
        log.debug(u'API :: all args: {0!r}', args)
        log.debug(u'API :: all kwargs: {0!r}', text_type(kwargs))

        commands = None
        if args:
            commands, args = args[0], args[1:]
        commands = kwargs.pop('cmd', commands)

        out_dict = {}
        if commands:
            commands = commands.split('|')
            multi_commands = len(commands) > 1
            for cmd in commands:
                cur_args, cur_kwargs = self.filter_params(cmd, args, kwargs)

                if len(cmd.split('_')) > 1:
                    cmd, cmd_index = cmd.split('_')

                log.debug(u'API :: {0}: {1}', cmd, cur_kwargs)
                if not (cmd in ('show.getbanner', 'show.getfanart', 'show.getnetworklogo', 'show.getposter') and
                        multi_commands):  # skip these cmd while chaining
                    try:
                        if cmd in function_mapper:
                            func = function_mapper.get(cmd)  # map function
                            func.rh = self  # add request handler to function
                            cur_out_dict = func(cur_args, cur_kwargs).run()  # call function and get response
                        elif _is_int(cmd):
                            cur_out_dict = TVDBShorthandWrapper(cur_args, cur_kwargs, cmd).run()
                        else:
                            cur_out_dict = _responds(RESULT_ERROR, 'No such cmd: {0!r}'.format(cmd))
                    except ApiError as error:  # Api errors that we raised, they are harmless
                        cur_out_dict = _responds(RESULT_ERROR, msg=text_type(error))
                else:  # if someone chained one of the forbidden commands they will get an error for this one cmd
                    cur_out_dict = _responds(RESULT_ERROR, msg='The cmd {0!r} is not supported while chaining'.format(cmd))

                if multi_commands:
                    # note: if duplicate commands are issued and one has an index defined it will override
                    # all others or the other way around, depending on the command order
                    # THIS IS NOT A BUG!
                    if cmd_index:  # do we need an index dict for this cmd ?
                        if cmd not in out_dict:
                            out_dict[cmd] = {}
                        out_dict[cmd][cmd_index] = cur_out_dict
                    else:
                        out_dict[cmd] = cur_out_dict
                else:
                    out_dict = cur_out_dict

            if multi_commands:  # if we had multiple commands we have to wrap it in a response dict
                out_dict = _responds(RESULT_SUCCESS, out_dict)
        else:  # index / no cmd given
            out_dict = CMD_(args, kwargs).run()

        return out_dict

    @staticmethod
    def filter_params(cmd, args, kwargs):
        """ return only params kwargs that are for cmd
            and rename them to a clean version (remove "<cmd>_")
            args are shared across all commands

            all args and kwargs are lowered

            cmd are separated by "|" e.g. &cmd=shows|future
            kwargs are name-spaced with "." e.g. show.indexerid=101501
            if a kwarg has no namespace asking it anyways (global)

            full e.g.
            /api?apikey=1234&cmd=show.seasonlist_asd|show.seasonlist_2&show.seasonlist_asd.indexerid=101501&show.seasonlist_2.indexerid=79488&sort=asc

            two calls of show.seasonlist
            one has the index "asd" the other one "2"
            the "indexerid" kwargs / params have the indexed cmd as a namespace
            and the kwarg / param "sort" is a used as a global
        """
        cur_args = []
        for arg in args:
            cur_args.append(arg.lower())
        cur_args = tuple(cur_args)

        cur_kwargs = {}
        for kwarg in kwargs:
            if kwarg.find(cmd + '.') == 0:
                clean_key = kwarg.rpartition('.')[2]
                cur_kwargs[clean_key] = kwargs[kwarg].lower()
            elif '.' not in kwarg:  # the kwarg was not name-spaced therefore a "global"
                cur_kwargs[kwarg] = kwargs[kwarg]
        return cur_args, cur_kwargs


class ApiCall(ApiHandler):
    _help = {'desc': 'This command is not documented. Please report this to the developers.'}

    def __init__(self, args, kwargs):
        # missing
        if hasattr(self, '_missing') and self._missing:
            self.run = self.return_missing

        # help
        if 'help' in kwargs:
            self.run = self.return_help

    def run(self):
        # override with real output function in subclass
        return {}

    def return_help(self):
        try:
            if self._requiredParams:
                pass
        except AttributeError:
            self._requiredParams = []
        try:
            if self._optionalParams:
                pass
        except AttributeError:
            self._optionalParams = []

        for paramDict, paramType in [(self._requiredParams, 'requiredParameters'),
                                     (self._optionalParams, 'optionalParameters')]:

            if paramType in self._help:
                for paramName in paramDict:
                    if paramName not in self._help[paramType]:
                        self._help[paramType][paramName] = {}
                    if paramDict[paramName]['allowedValues']:
                        self._help[paramType][paramName]['allowedValues'] = paramDict[paramName]['allowedValues']
                    else:
                        self._help[paramType][paramName]['allowedValues'] = 'see desc'
                    self._help[paramType][paramName]['defaultValue'] = paramDict[paramName]['defaultValue']
                    self._help[paramType][paramName]['type'] = paramDict[paramName]['type']

            elif paramDict:
                for paramName in paramDict:
                    self._help[paramType] = {}
                    self._help[paramType][paramName] = paramDict[paramName]
            else:
                self._help[paramType] = {}
        msg = 'No description available'
        if 'desc' in self._help:
            msg = self._help['desc']
        return _responds(RESULT_SUCCESS, self._help, msg)

    def return_missing(self):
        if len(self._missing) == 1:
            msg = 'The required parameter: {0!r} was not set'.format(self._missing[0])
        else:
            msg = 'The required parameters: {0!r} were not set'.format("','".join(self._missing))
        return _responds(RESULT_ERROR, msg=msg)

    def check_params(self, args, kwargs, key, default, required, arg_type, allowed_values):

        """ function to check passed params for the shorthand wrapper
            and to detect missing/required params
        """

        # auto-select indexer
        if key in itervalues(INDEXER_IDS):
            if 'tvdbid' in kwargs:
                key = 'tvdbid'

            self.indexer = next(k for k, v in iteritems(INDEXER_IDS) if v == key)

        missing = True
        org_default = default

        if arg_type == 'bool':
            allowed_values = [0, 1]

        if args:
            default = args[0]
            missing = False
            args = args[1:]
        if kwargs.get(key):
            default = kwargs.get(key)
            missing = False
        if required:
            if hasattr(self, '_requiredParams') and isinstance(self._requiredParams, list):
                self._requiredParams.append(key)
            else:
                self._missing = []
                self._requiredParams = {key: {'allowedValues': allowed_values,
                                              'defaultValue': org_default,
                                              'type': arg_type}}

            if missing and key not in self._missing:
                self._missing.append(key)
        else:
            try:
                self._optionalParams[key] = {'allowedValues': allowed_values,
                                             'defaultValue': org_default,
                                             'type': arg_type}
            except AttributeError:
                self._optionalParams = {key: {'allowedValues': allowed_values,
                                              'defaultValue': org_default,
                                              'type': arg_type}}

        if default:
            default = self._check_param_type(default, key, arg_type)
            self._check_param_value(default, key, allowed_values)

        return default, args

    def _check_param_type(self, value, name, arg_type):
        """ checks if value can be converted / parsed to arg_type
            will raise an error on failure
            or will convert it to arg_type and return new converted value
            can check for:
            - int: will be converted into int
            - bool: will be converted to False / True
            - list: will always return a list
            - string: will do nothing for now
            - ignore: will ignore it, just like "string"
        """
        error = False
        if arg_type == 'int':
            if _is_int(value):
                value = int(value)
            else:
                error = True
        elif arg_type == 'bool':
            if value in ('0', '1'):
                value = bool(int(value))
            elif value in ('true', 'True', 'TRUE'):
                value = True
            elif value in ('false', 'False', 'FALSE'):
                value = False
            elif value not in (True, False):
                error = True
        elif arg_type == 'list':
            value = value.split('|')
        elif arg_type == 'string':
            pass
        elif arg_type == 'ignore':
            pass
        else:
            log.error(u'API :: Invalid param type: {0!r} can not be checked. Ignoring it.', arg_type)

        if error:
            # this is a real ApiError !!
            raise ApiError(
                u'param {0!r} with given value {1!r} could not be parsed into {2!r}'.format(name, value, arg_type)
            )

        return value

    def _check_param_value(self, value, name, allowed_values):
        """ will check if value (or all values in it ) are in allowed values
            will raise an exception if value is "out of range"
            if bool(allowed_value) is False a check is not performed and all values are excepted
        """
        if allowed_values:
            error = False
            if isinstance(value, list):
                for item in value:
                    if item not in allowed_values:
                        error = True
            else:
                if value not in allowed_values:
                    error = True

            if error:
                # this is kinda a ApiError but raising an error is the only way of quitting here
                raise ApiError(
                    u'param: {0!r} with given value {1!r}  is out of allowed range {2!r}'.format(
                        name, value, allowed_values
                    )
                )


class TVDBShorthandWrapper(ApiCall):
    _help = {'desc': 'This is an internal function wrapper. Call the help command directly for more information.'}

    def __init__(self, args, kwargs, sid):
        self.origArgs = args
        self.kwargs = kwargs
        self.sid = sid

        self.s, args = self.check_params(args, kwargs, 's', None, False, 'ignore', [])
        self.e, args = self.check_params(args, kwargs, 'e', None, False, 'ignore', [])
        self.args = args

        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ internal function wrapper """
        args = (self.sid,) + self.origArgs
        if self.e:
            return CMD_Episode(args, self.kwargs).run()
        elif self.s:
            return CMD_ShowSeasons(args, self.kwargs).run()
        else:
            return CMD_Show(args, self.kwargs).run()


# ###############################
#       helper functions        #
# ###############################

def _is_int(data):
    try:
        int(data)
    except (TypeError, ValueError, OverflowError):
        return False
    else:
        return True


def _rename_element(dict_obj, old_key, new_key):
    try:
        dict_obj[new_key] = dict_obj[old_key]
        del dict_obj[old_key]
    except (ValueError, TypeError, NameError):
        pass
    return dict_obj


def _responds(result_type, data=None, msg=''):
    """
    result is a string of given "type" (success/failure/timeout/error)
    message is a human readable string, can be empty
    data is either a dict or a array, can be a empty dict or empty array
    """
    return {'result': result_type_map[result_type],
            'message': msg,
            'data': {} if not data else data}


def _ordinal_to_date(ordinal, date_format):
    x = int(ordinal)
    return date.fromordinal(x).strftime(date_format) if x >= 1 else ''


def _ordinal_to_date_form(ordinal):
    return _ordinal_to_date(ordinal, dateFormat)


def _ordinal_to_datetime_form(ordinal):
    # workaround for episodes with no air date
    return _ordinal_to_date(ordinal, dateTimeFormat)


quality_map = OrderedDict((
    ('sdtv', Quality.SDTV),
    ('sddvd', Quality.SDDVD),
    ('hdtv', Quality.HDTV),
    ('rawhdtv', Quality.RAWHDTV),
    ('fullhdtv', Quality.FULLHDTV),
    ('hdwebdl', Quality.HDWEBDL),
    ('fullhdwebdl', Quality.FULLHDWEBDL),
    ('hdbluray', Quality.HDBLURAY),
    ('fullhdbluray', Quality.FULLHDBLURAY),
    ('uhd_4k_tv', Quality.UHD_4K_TV),
    ('uhd_4k_webdl', Quality.UHD_4K_WEBDL),
    ('uhd_4k_bluray', Quality.UHD_4K_BLURAY),
    ('uhd_8k_tv', Quality.UHD_8K_TV),
    ('uhd_8k_webdl', Quality.UHD_8K_WEBDL),
    ('uhd_8k_bluray', Quality.UHD_8K_BLURAY),
    ('unknown', Quality.UNKNOWN),
))


def _map_quality(show_obj):
    mapped_quality = {v: k for k, v in viewitems(quality_map)}

    allowed_qualities = []
    preferred_qualities = []

    i_quality_id, a_quality_id = Quality.split_quality(int(show_obj))
    if i_quality_id:
        for quality in i_quality_id:
            allowed_qualities.append(mapped_quality[quality])
    if a_quality_id:
        for quality in a_quality_id:
            preferred_qualities.append(mapped_quality[quality])
    return allowed_qualities, preferred_qualities


def _get_root_dirs():
    if not app.ROOT_DIRS:
        return {}

    root_dir = {}
    default_index = int(app.ROOT_DIRS[0])
    root_dir['default_index'] = default_index
    # clean up the list: replace %xx escapes with single-character equivalent
    # and remove default_index value from list (this fixes the offset)
    root_dirs = [
        unquote_plus(x)
        for x in app.ROOT_DIRS[1:]
    ]

    try:
        default_dir = root_dirs[default_index]
    except IndexError:
        return {}

    dir_list = []
    for root_dir in root_dirs:
        valid = 1
        try:
            os.listdir(root_dir)
        except OSError:
            valid = 0
        default = 0
        if root_dir is default_dir:
            default = 1

        cur_dir = {
            'valid': valid,
            'location': root_dir,
            'default': default
        }
        dir_list.append(cur_dir)

    return dir_list


class ApiError(Exception):
    """
    Generic API error
    """


class IntParseError(Exception):
    """
    A value could not be parsed into an int, but should be parse-able to an int
    """


# -------------------------------------------------------------------------------------#


class CMD_Help(ApiCall):
    _help = {
        'desc': 'Get help about a given command',
        'optionalParameters': {
            'subject': {'desc': 'The name of the command to get the help of'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.subject, args = self.check_params(args, kwargs, 'subject', 'help', False, 'string', list(function_mapper))
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get help about a given command """
        if self.subject in function_mapper:
            out = _responds(RESULT_SUCCESS, function_mapper.get(self.subject)((), {'help': 1}).run())
        else:
            out = _responds(RESULT_FAILURE, msg='No such cmd')
        return out


class CMD_ComingEpisodes(ApiCall):
    _help = {
        'desc': 'Get the coming episodes',
        'optionalParameters': {
            'sort': {'desc': 'Change the sort order'},
            'type': {'desc': 'One or more categories of coming episodes, separated by |'},
            'paused': {
                'desc': '0 to exclude paused shows, 1 to include them, or omitted to use Medusa default value'
            },
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.sort, args = self.check_params(args, kwargs, 'sort', 'date', False, 'string', list(ComingEpisodes.sorts))
        self.type, args = self.check_params(args, kwargs, 'type', '|'.join(ComingEpisodes.categories), False, 'list',
                                            ComingEpisodes.categories)
        self.paused, args = self.check_params(args, kwargs, 'paused', bool(app.COMING_EPS_DISPLAY_PAUSED), False,
                                              'bool', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the coming episodes """
        grouped_coming_episodes = ComingEpisodes.get_coming_episodes(self.type, self.sort, True, self.paused)
        data = {section: [] for section in grouped_coming_episodes}

        for section, coming_episodes in iteritems(grouped_coming_episodes):
            for coming_episode in coming_episodes:
                data[section].append({
                    'airdate': coming_episode['airdate'],
                    'airs': coming_episode['airs'],
                    'ep_name': coming_episode['name'],
                    'ep_plot': coming_episode['description'],
                    'episode': coming_episode['episode'],
                    'indexerid': coming_episode['indexer_id'],
                    'network': coming_episode['network'],
                    'paused': coming_episode['paused'],
                    'quality': coming_episode['quality'],
                    'season': coming_episode['season'],
                    'show_name': coming_episode['show_name'],
                    'show_status': coming_episode['status'],
                    'tvdbid': coming_episode['tvdbid'],
                    'weekday': coming_episode['weekday']
                })

        return _responds(RESULT_SUCCESS, data)


class CMD_Episode(ApiCall):
    _help = {
        'desc': 'Get detailed information about an episode',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
            'season': {'desc': 'The season number'},
            'episode': {'desc': 'The episode number'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'full_path': {
                'desc': 'Return the full absolute show location (if valid, and True), or the relative show location'
            },
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        self.s, args = self.check_params(args, kwargs, 'season', None, True, 'int', [])
        self.e, args = self.check_params(args, kwargs, 'episode', None, True, 'int', [])
        # optional
        self.full_path, args = self.check_params(args, kwargs, 'full_path', False, False, 'bool', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """Get detailed information about an episode."""
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            'SELECT name, description, airdate, status, quality, location, file_size, release_name, subtitles '
            'FROM tv_episodes WHERE indexer = ? AND showid = ? AND episode = ? AND season = ?',
            [INDEXER_TVDBV2, self.indexerid, self.e, self.s])
        if not len(sql_results) == 1:
            raise ApiError('Episode not found')
        episode = sql_results[0]
        # handle path options
        # absolute vs relative vs broken
        show_path = None
        try:
            show_path = show_obj.validate_location
        except ShowDirectoryNotFoundException:
            pass

        if not show_path:  # show dir is broken ... episode path will be empty
            episode['location'] = ''
        elif not self.full_path:
            # using the length because lstrip() removes to much
            show_path_length = len(show_path) + 1  # the / or \ yeah not that nice i know
            episode['location'] = episode['location'][show_path_length:]

        # convert stuff to human form
        if try_int(episode['airdate'], 1) > 693595:  # 1900
            episode['airdate'] = sbdatetime.sbdatetime.sbfdate(sbdatetime.sbdatetime.convert_to_setting(
                network_timezones.parse_date_time(int(episode['airdate']), show_obj.airs, show_obj.network)),
                d_preset=dateFormat)
        else:
            episode['airdate'] = 'Never'

        status, quality = int(episode['status']), int(episode['quality'])
        episode['status'] = statusStrings[status]
        episode['quality'] = get_quality_string(quality)
        episode['file_size_human'] = pretty_file_size(episode['file_size'])

        return _responds(RESULT_SUCCESS, episode)


class CMD_EpisodeSearch(ApiCall):
    _help = {
        'desc': 'Search for an episode. The response might take some time.',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
            'season': {'desc': 'The season number'},
            'episode': {'desc': 'The episode number'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        self.s, args = self.check_params(args, kwargs, 'season', None, True, 'int', [])
        self.e, args = self.check_params(args, kwargs, 'episode', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Search for an episode """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        # retrieve the episode object and fail if we can't get one
        ep_obj = show_obj.get_episode(self.s, self.e)
        if isinstance(ep_obj, string_types):
            return _responds(RESULT_FAILURE, msg='Episode not found')

        # make a queue item for it and put it on the queue
        ep_queue_item = BacklogQueueItem(show_obj, [ep_obj])
        app.forced_search_queue_scheduler.action.add_item(ep_queue_item)  # @UndefinedVariable

        # wait until the queue item tells us whether it worked or not
        while ep_queue_item.success is None:  # @UndefinedVariable
            time.sleep(1)

        # return the correct json value
        if ep_queue_item.success:
            return _responds(RESULT_SUCCESS, {'quality': get_quality_string(ep_obj.quality)},
                             'Snatched ({0})'.format(get_quality_string(ep_obj.quality)))

        return _responds(RESULT_FAILURE, msg='Unable to find episode')


class CMD_EpisodeSetStatus(ApiCall):
    _help = {
        'desc': 'Set the status of an episode or a season (when no episode is provided)',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
            'season': {'desc': 'The season number'},
            'status': {'desc': 'The status of the episode or season'}
        },
        'optionalParameters': {
            'episode': {'desc': 'The episode number'},
            'force': {'desc': 'True to replace existing downloaded episode or season, False otherwise'},
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        self.s, args = self.check_params(args, kwargs, 'season', None, True, 'int', [])
        self.status, args = self.check_params(args, kwargs, 'status', None, True, 'string',
                                              ['wanted', 'skipped', 'ignored', 'failed'])
        # optional
        self.e, args = self.check_params(args, kwargs, 'episode', None, False, 'int', [])
        self.force, args = self.check_params(args, kwargs, 'force', False, False, 'bool', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Set the status of an episode or a season (when no episode is provided) """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        # convert the string status to a int
        for status in statusStrings:
            if text_type(statusStrings[status]).lower() == text_type(self.status).lower():
                self.status = status
                break
        else:  # if we don't break out of the for loop we got here.
            # the allowed values has at least one item that could not be matched against the internal status strings
            raise ApiError('The status string could not be matched to a status. Report to Devs!')

        if self.e:
            ep_obj = show_obj.get_episode(self.s, self.e)
            if not ep_obj:
                return _responds(RESULT_FAILURE, msg='Episode not found')
            ep_list = [ep_obj]
        else:
            # get all episode numbers from self, season
            ep_list = show_obj.get_all_episodes(season=self.s)

        def _ep_result(result_code, ep, msg=''):
            return {'season': ep.season, 'episode': ep.episode, 'status': statusStrings[ep.status],
                    'result': result_type_map[result_code], 'message': msg}

        ep_results = []
        failure = False
        start_backlog = False
        segments = {}

        sql_l = []
        for ep_obj in ep_list:
            with ep_obj.lock:
                if self.status == WANTED:
                    # figure out what episodes are wanted so we can backlog them
                    if ep_obj.season in segments:
                        segments[ep_obj.season].append(ep_obj)
                    else:
                        segments[ep_obj.season] = [ep_obj]

                # don't let them mess up UN-AIRED episodes
                if ep_obj.status == UNAIRED:
                    # setting the status of an un-aired is only considered a failure if we directly wanted this episode, but is ignored on a season request
                    if self.e is not None:
                        ep_results.append(
                            _ep_result(RESULT_FAILURE, ep_obj, 'Refusing to change status because it is UN-AIRED'))
                        failure = True
                    continue

                if self.status == FAILED and not app.USE_FAILED_DOWNLOADS:
                    ep_results.append(_ep_result(RESULT_FAILURE, ep_obj,
                                                 'Refusing to change status to FAILED because failed download handling is disabled'))
                    failure = True
                    continue

                # allow the user to force setting the status for an already downloaded episode
                if ep_obj.status in [DOWNLOADED, ARCHIVED] and not self.force:
                    ep_results.append(
                        _ep_result(
                            RESULT_FAILURE, ep_obj,
                            'Refusing to change status because it is already marked as DOWNLOADED'
                        )
                    )
                    failure = True
                    continue

                ep_obj.status = self.status
                sql_l.append(ep_obj.get_sql())

                if self.status == WANTED:
                    start_backlog = True
                ep_results.append(_ep_result(RESULT_SUCCESS, ep_obj))

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

        extra_msg = ''
        if start_backlog:
            for season, segment in iteritems(segments):
                cur_backlog_queue_item = BacklogQueueItem(show_obj, segment)
                app.search_queue_scheduler.action.add_item(cur_backlog_queue_item)  # @UndefinedVariable

                log.info(u'API :: Starting backlog for {0} season {1} because some episodes were set to WANTED',
                         show_obj.name, season)

            extra_msg = ' Backlog started'

        if failure:
            return _responds(RESULT_FAILURE, ep_results, 'Failed to set all or some status. Check data. {0}'.format(extra_msg))
        else:
            return _responds(RESULT_SUCCESS, msg='All status set successfully. {0}'.format(extra_msg))


class CMD_SubtitleSearch(ApiCall):
    _help = {
        'desc': 'Search for an episode subtitles. The response might take some time.',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
            'season': {'desc': 'The season number'},
            'episode': {'desc': 'The episode number'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        self.s, args = self.check_params(args, kwargs, 'season', None, True, 'int', [])
        self.e, args = self.check_params(args, kwargs, 'episode', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Search for an episode subtitles """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        # retrieve the episode object and fail if we can't get one
        ep_obj = show_obj.get_episode(self.s, self.e)
        if isinstance(ep_obj, string_types):
            return _responds(RESULT_FAILURE, msg='Episode not found')

        try:
            new_subtitles = ep_obj.download_subtitles()
        except Exception:
            return _responds(RESULT_FAILURE, msg='Unable to find subtitles')

        if new_subtitles:
            new_languages = [subtitles.name_from_code(code) for code in new_subtitles]
            status = 'New subtitles downloaded: {0}'.format(', '.join(new_languages))
            response = _responds(RESULT_SUCCESS, msg='New subtitles found')
        else:
            status = 'No subtitles downloaded'
            response = _responds(RESULT_FAILURE, msg='Unable to find subtitles')

        ui.notifications.message('Subtitles Search', status)

        return response


class CMD_Exceptions(ApiCall):
    _help = {
        'desc': 'Get the scene exceptions for all or a given show',
        'optionalParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, False, 'int', [])

        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the scene exceptions for all or a given show """
        cache_db_con = db.DBConnection('cache.db')

        if self.indexerid is None:
            sql_results = cache_db_con.select("SELECT show_name, indexer_id AS 'indexerid' FROM scene_exceptions")
            scene_exceptions = {}
            for row in sql_results:
                indexerid = row['indexerid']
                if indexerid not in scene_exceptions:
                    scene_exceptions[indexerid] = []
                scene_exceptions[indexerid].append(row['show_name'])

        else:
            show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
            if not show_obj:
                return _responds(RESULT_FAILURE, msg='Show not found')

            sql_results = cache_db_con.select(
                "SELECT show_name, indexer_id AS 'indexerid' FROM scene_exceptions WHERE indexer_id = ?",
                [self.indexerid])
            scene_exceptions = []
            for row in sql_results:
                scene_exceptions.append(row['show_name'])

        return _responds(RESULT_SUCCESS, scene_exceptions)


class CMD_History(ApiCall):
    _help = {
        'desc': 'Get the downloaded and/or snatched history',
        'optionalParameters': {
            'limit': {'desc': 'The maximum number of results to return'},
            'type': {'desc': 'Only get some entries. No value will returns every type'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.limit, args = self.check_params(args, kwargs, 'limit', 100, False, 'int', [])
        self.type, args = self.check_params(args, kwargs, 'type', None, False, 'string', ['downloaded', 'snatched'])
        self.type = self.type.lower() if isinstance(self.type, string_types) else None

        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the downloaded and/or snatched history """
        history = History().get(self.limit, self.type).detailed

        def make_result(cur_item, cur_type):
            """
            Make an API result from a history item

            :param cur_item: to convert to API item
            :param cur_type: the type of action to return

            :returns: an API result
            """

            def convert_date(history_date):
                """
                Convert date from a history date to datetime format
                :param history_date: a date from the history
                :return: a formatted date string
                """
                return datetime.strptime(
                    text_type(history_date),
                    History.date_format
                ).strftime(dateTimeFormat)

            if cur_type in (statusStrings[cur_item.action].lower(), None):
                return {
                    'date': convert_date(cur_item.date),
                    'episode': cur_item.episode,
                    'indexer': cur_item.indexer_id,
                    'provider': cur_item.provider,
                    'quality': get_quality_string(cur_item.quality),
                    'resource': os.path.basename(cur_item.resource),
                    'resource_path': os.path.dirname(cur_item.resource),
                    'season': cur_item.season,
                    'show_name': cur_item.show_name,
                    'status': statusStrings[cur_item.action],
                    'show_id': cur_item.show_id,
                }

        results = [make_result(x, self.type) for x in history if x]
        return _responds(RESULT_SUCCESS, results)


class CMD_HistoryClear(ApiCall):
    _help = {'desc': 'Clear the entire history'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Clear the entire history """
        History().clear()

        return _responds(RESULT_SUCCESS, msg='History cleared')


class CMD_HistoryTrim(ApiCall):
    _help = {'desc': 'Trim history entries older than 30 days'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Trim history entries older than 30 days """
        History().trim()

        return _responds(RESULT_SUCCESS, msg='Removed history entries older than 30 days')


class CMD_Failed(ApiCall):
    _help = {
        'desc': 'Get the failed downloads',
        'optionalParameters': {
            'limit': {'desc': 'The maximum number of results to return'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.limit, args = self.check_params(args, kwargs, 'limit', 100, False, 'int', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the failed downloads """

        failed_db_con = db.DBConnection('failed.db')

        u_limit = min(int(self.limit), 100)
        if u_limit == 0:
            sql_results = failed_db_con.select('SELECT * FROM failed')
        else:
            sql_results = failed_db_con.select('SELECT * FROM failed LIMIT ?', [u_limit])

        return _responds(RESULT_SUCCESS, sql_results)


class CMD_Backlog(ApiCall):
    _help = {'desc': 'Get the backlogged episodes'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the backlogged episodes """

        shows = []

        main_db_con = db.DBConnection()
        for cur_show in app.showList:

            show_eps = []

            sql_results = main_db_con.select(
                'SELECT tv_episodes.*, tv_shows.paused '
                'FROM tv_episodes '
                'INNER JOIN tv_shows ON tv_episodes.showid = tv_shows.indexer_id '
                'AND tv_episodes.indexer = tv_shows.indexer '
                'WHERE tv_episodes.indexer = ? AND showid = ? AND paused = 0 ORDER BY season DESC, episode DESC',
                [cur_show.indexer, cur_show.series_id])

            for cur_result in sql_results:

                cur_ep_cat = cur_show.get_overview(
                    cur_result['status'], cur_result['quality'], manually_searched=cur_result['manually_searched']
                )
                if cur_ep_cat and cur_ep_cat in (Overview.WANTED, Overview.QUAL):
                    show_eps.append(cur_result)

            if show_eps:
                shows.append({
                    'indexerid': cur_show.indexerid,
                    'show_name': cur_show.name,
                    'status': cur_show.status,
                    'episodes': show_eps
                })

        return _responds(RESULT_SUCCESS, shows)


class CMD_Logs(ApiCall):
    _help = {
        'desc': 'Get the logs',
        'optionalParameters': {
            'min_level': {
                'desc':
                    'The minimum level classification of log entries to return. '
                    'Each level inherits its above levels: debug < info < warning < error'
            },
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.min_level, args = self.check_params(args, kwargs, 'min_level', 'info', False, 'string',
                                                 ['error', 'warning', 'info', 'debug'])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the logs """
        # 10 = Debug / 20 = Info / 30 = Warning / 40 = Error
        min_level = LOGGING_LEVELS[text_type(self.min_level).upper()]
        data = [line for line in read_loglines(formatter=text_type, max_lines=50,
                                               predicate=lambda l: filter_logline(l, min_level=min_level,
                                                                                  thread_name=lambda
                                                                                  name: name != 'TORNADO'))]
        return _responds(RESULT_SUCCESS, data)


class CMD_LogsClear(ApiCall):
    _help = {
        'desc': 'Clear the logs',
        'optionalParameters': {
            'level': {'desc': 'The level of logs to clear'},
        },
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.level, args = self.check_params(args, kwargs, 'level', 'warning', False, 'string', ['warning', 'error'])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Clear the logs """
        if self.level == 'error':
            msg = 'Error logs cleared'

            classes.ErrorViewer.clear()
        elif self.level == 'warning':
            msg = 'Warning logs cleared'

            classes.WarningViewer.clear()
        else:
            return _responds(RESULT_FAILURE, msg='Unknown log level: {0}'.format(self.level))

        return _responds(RESULT_SUCCESS, msg=msg)


class CMD_PostProcess(ApiCall):
    _help = {
        'desc': 'Manually post-process the files in the download folder',
        'optionalParameters': {
            'path': {'desc': 'The path to the folder to post-process'},
            'force_replace': {'desc': 'Force already post-processed files to be post-processed again'},
            'return_data': {'desc': 'Returns the result of the post-process'},
            'process_method': {'desc': 'How should valid post-processed files be handled'},
            'is_priority': {'desc': 'Replace the file even if it exists in a higher quality'},
            'delete_files': {'desc': 'Delete files and folders like auto processing'},
            'failed': {'desc': 'Mark download as failed'},
            'type': {'desc': 'The type of post-process being requested'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.path, args = self.check_params(args, kwargs, 'path', None, False, 'string', [])
        self.force_replace, args = self.check_params(args, kwargs, 'force_replace', False, False, 'bool', [])
        self.return_data, args = self.check_params(args, kwargs, 'return_data', False, False, 'bool', [])
        self.process_method, args = self.check_params(args, kwargs, 'process_method', False, False, 'string',
                                                      ['copy', 'symlink', 'hardlink', 'move', 'reflink'])
        self.is_priority, args = self.check_params(args, kwargs, 'is_priority', False, False, 'bool', [])
        self.delete_files, args = self.check_params(args, kwargs, 'delete_files', False, False, 'bool', [])
        self.failed, args = self.check_params(args, kwargs, 'failed', False, False, 'bool', [])
        self.type, args = self.check_params(args, kwargs, 'type', 'auto', None, 'string', ['auto', 'manual'])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Manually post-process the files in the download folder """
        if not self.path and not app.TV_DOWNLOAD_DIR:
            return _responds(RESULT_FAILURE, msg='You need to provide a path or set TV Download Dir')

        if not self.path:
            self.path = app.TV_DOWNLOAD_DIR

        if not self.type:
            self.type = 'manual'

        data = app.post_processor_scheduler.action.run(
            path=self.path,
            process_method=self.process_method,
            force=self.force_replace,
            is_priority=self.is_priority,
            delete_on=self.delete_files,
            failed=self.failed,
            proc_type=self.type
        )

        if not self.return_data:
            data = ''

        return _responds(RESULT_SUCCESS, data=data, msg='Started post-process for {0}'.format(self.path))


class CMD_(ApiCall):
    _help = {'desc': 'Get miscellaneous information about Medusa'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ dGet miscellaneous information about Medusa """
        data = {'sr_version': app.BRANCH, 'api_version': self.version,
                'api_commands': sorted(function_mapper.keys())}
        return _responds(RESULT_SUCCESS, data)


class CMD_AddRootDir(ApiCall):
    _help = {
        'desc': 'Add a new root (parent) directory to Medusa',
        'requiredParameters': {
            'location': {'desc': 'The full path to the new root (parent) directory'},
        },
        'optionalParameters': {
            'default': {'desc': 'Make this new location the default root (parent) directory'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.location, args = self.check_params(args, kwargs, 'location', None, True, 'string', [])
        # optional
        self.default, args = self.check_params(args, kwargs, 'default', False, False, 'bool', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Add a new root (parent) directory to Medusa """

        self.location = unquote_plus(self.location)
        location_matched = False
        index = 0

        # disallow adding/setting an invalid dir
        if not os.path.isdir(self.location):
            return _responds(RESULT_FAILURE, msg='Location is invalid')

        root_dirs = []

        if not app.ROOT_DIRS:
            self.default = True
        else:
            index = int(app.ROOT_DIRS[0])
            # clean up the list: replace %xx escapes with single-character equivalent
            # and remove default_index value from list (this fixes the offset)
            root_dirs = [
                unquote_plus(directory)
                for directory in app.ROOT_DIRS[1:]
            ]
            for directory in root_dirs:
                if directory == self.location:
                    location_matched = True
                    if self.default:
                        index = root_dirs.index(self.location)
                    break

        if not location_matched:
            if self.default:
                root_dirs.insert(0, self.location)
            else:
                root_dirs.append(self.location)

        root_dirs_new = [
            unquote_plus(directory)
            for directory in root_dirs
        ]
        # reinsert index value in the list
        root_dirs_new.insert(0, index)
        app.ROOT_DIRS = root_dirs_new
        return _responds(RESULT_SUCCESS, _get_root_dirs(), msg='Root directories updated')


class CMD_CheckVersion(ApiCall):
    _help = {'desc': 'Check if a new version of Medusa is available'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        check_version = CheckVersion()
        needs_update = check_version.check_for_new_version()

        data = {
            'current_version': {
                'branch': check_version.get_branch(),
                'commit': check_version.updater.current_commit_hash,
                'version': check_version.updater.current_version,
            },
            'latest_version': {
                'branch': check_version.get_branch(),
                'commit': check_version.updater.newest_commit_hash,
                'version': check_version.updater.newest_version,
            },
            'commits_offset': check_version.updater.commits_behind,
            'needs_update': needs_update,
        }

        return _responds(RESULT_SUCCESS, data)


class CMD_CheckScheduler(ApiCall):
    _help = {'desc': 'Get information about the scheduler'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get information about the scheduler """
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select('SELECT last_backlog FROM info')

        backlog_paused = app.search_queue_scheduler.action.is_backlog_paused()
        backlog_running = app.search_queue_scheduler.action.is_backlog_in_progress()
        next_backlog = app.backlog_search_scheduler.next_run().strftime(dateFormat)

        data = {'backlog_is_paused': int(backlog_paused), 'backlog_is_running': int(backlog_running),
                'last_backlog': _ordinal_to_date_form(sql_results[0]['last_backlog']),
                'next_backlog': next_backlog}
        return _responds(RESULT_SUCCESS, data)


class CMD_DeleteRootDir(ApiCall):
    _help = {
        'desc': 'Delete a root (parent) directory from Medusa',
        'requiredParameters': {
            'location': {'desc': 'The full path to the root (parent) directory to remove'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.location, args = self.check_params(args, kwargs, 'location', None, True, 'string', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Delete a root (parent) directory from Medusa """
        if not app.ROOT_DIRS:
            return _responds(RESULT_FAILURE, _get_root_dirs(), msg='No root directories detected')

        index = int(app.ROOT_DIRS[0])
        # clean up the list: replace %xx escapes with single-character equivalent
        # and remove default_index value from list (this fixes the offset)
        root_dirs = [
            unquote_plus(directory)
            for directory in app.ROOT_DIRS[1:]
        ]
        default_dir = root_dirs[index]
        location = unquote_plus(self.location)
        try:
            root_dirs.remove(location)
        except ValueError:
            result = RESULT_FAILURE
            msg = 'Location not in root directories'
            return _responds(result, _get_root_dirs(), msg=msg)

        try:
            index = root_dirs.index(default_dir)
        except ValueError:
            if default_dir == location:
                result = RESULT_DENIED
                msg = 'Default directory cannot be deleted; Please set a new default directory.'
            else:
                result = RESULT_ERROR
                msg = 'Default directory not found'
        else:
            root_dirs.insert(0, index)
            app.ROOT_DIRS = root_dirs
            result = RESULT_SUCCESS
            msg = 'Root directory {0} deleted'.format(location)

        return _responds(result, _get_root_dirs(), msg=msg)


class CMD_GetDefaults(ApiCall):
    _help = {'desc': "Get Medusa's user default configuration value"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get Medusa's user default configuration value """

        any_qualities, best_qualities = _map_quality(app.QUALITY_DEFAULT)

        data = {'status': statusStrings[app.STATUS_DEFAULT].lower(),
                'flatten_folders': int(not app.SEASON_FOLDERS_DEFAULT),
                'season_folders': int(app.SEASON_FOLDERS_DEFAULT),
                'initial': any_qualities,
                'archive': best_qualities,
                'future_show_paused': int(app.COMING_EPS_DISPLAY_PAUSED)}
        return _responds(RESULT_SUCCESS, data)


class CMD_GetMessages(ApiCall):
    _help = {'desc': 'Get all messages'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        messages = []
        for cur_notification in ui.notifications.get_notifications(self.rh.request.remote_ip):
            messages.append({'title': cur_notification.title,
                             'message': cur_notification.message,
                             'type': cur_notification.notification_type})
        return _responds(RESULT_SUCCESS, messages)


class CMD_GetRootDirs(ApiCall):
    _help = {'desc': 'Get all root (parent) directories'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get all root (parent) directories """

        return _responds(RESULT_SUCCESS, _get_root_dirs())


class CMD_PauseBacklog(ApiCall):
    _help = {
        'desc': 'Pause or un-pause the backlog search',
        'optionalParameters': {
            'pause ': {'desc': 'True to pause the backlog search, False to un-pause it'}
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.pause, args = self.check_params(args, kwargs, 'pause', False, False, 'bool', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Pause or un-pause the backlog search """
        if self.pause:
            app.search_queue_scheduler.action.pause_backlog()  # @UndefinedVariable
            return _responds(RESULT_SUCCESS, msg='Backlog paused')
        else:
            app.search_queue_scheduler.action.unpause_backlog()  # @UndefinedVariable
            return _responds(RESULT_SUCCESS, msg='Backlog un-paused')


class CMD_Ping(ApiCall):
    _help = {'desc': 'Ping Medusa to check if it is running'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Ping Medusa to check if it is running """
        if app.started:
            return _responds(RESULT_SUCCESS, {'pid': app.PID}, 'Pong')
        else:
            return _responds(RESULT_SUCCESS, msg='Pong')


class CMD_Restart(ApiCall):
    _help = {'desc': 'Restart Medusa'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Restart Medusa """
        if not Restart.restart(app.PID):
            return _responds(RESULT_FAILURE, msg='Medusa can not be restarted')

        return _responds(RESULT_SUCCESS, msg='Medusa is restarting...')


class CMD_SearchIndexers(ApiCall):
    _help = {
        'desc': 'Search for a show with a given name on all the indexers, in a specific language',
        'optionalParameters': {
            'name': {'desc': 'The name of the show you want to search for'},
            'indexerid': {'desc': 'Unique ID of a show'},
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'lang': {'desc': 'The 2-letter language code of the desired show'},
        }
    }

    def __init__(self, args, kwargs):
        self.valid_languages = indexerApi().config['langabbv_to_id']
        # required
        # optional
        self.name, args = self.check_params(args, kwargs, 'name', None, False, 'string', [])
        self.lang, args = self.check_params(args, kwargs, 'lang', app.INDEXER_DEFAULT_LANGUAGE, False, 'string',
                                            list(self.valid_languages))
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, False, 'int', [])

        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Search for a show with a given name on all the indexers, in a specific language """

        results = []
        lang_id = self.valid_languages[self.lang]

        if isinstance(self.name, binary_type):
            self.name = self.name.decode('utf-8')

        if self.name and not self.indexerid:  # only name was given
            for _indexer in indexerApi().indexers if self.indexer == 0 else [int(self.indexer)]:
                indexer_api_params = indexerApi(_indexer).api_params.copy()

                if self.lang and not self.lang == app.INDEXER_DEFAULT_LANGUAGE:
                    indexer_api_params['language'] = self.lang

                indexer_api_params['actors'] = False
                indexer_api_params['custom_ui'] = classes.AllShowsListUI

                indexer_api = indexerApi(_indexer).indexer(**indexer_api_params)

                try:
                    api_data = indexer_api[self.name]
                except (IndexerShowNotFound, IndexerError):
                    log.warning(u'API :: Unable to find show with name {0}', self.name)
                    continue

                for cur_series in api_data:
                    results.append({INDEXER_IDS[_indexer]: int(cur_series['id']),
                                    'name': cur_series['seriesname'],
                                    'first_aired': cur_series['firstaired'],
                                    'indexer': int(_indexer)})

            return _responds(RESULT_SUCCESS, {'results': results, 'langid': lang_id})

        elif self.indexerid:
            for _indexer in indexerApi().indexers if self.indexer == 0 else [int(self.indexer)]:
                indexer_api_params = indexerApi(_indexer).api_params.copy()

                if self.lang and not self.lang == app.INDEXER_DEFAULT_LANGUAGE:
                    indexer_api_params['language'] = self.lang

                indexer_api_params['actors'] = False

                indexer_api = indexerApi(_indexer).indexer(**indexer_api_params)

                try:
                    my_show = indexer_api[int(self.indexerid)]
                except (IndexerShowNotFound, IndexerError):
                    log.warning(u'API :: Unable to find show with id {0}', self.indexerid)
                    return _responds(RESULT_SUCCESS, {'results': [], 'langid': lang_id})

                if not my_show.data['seriesname']:
                    log.debug(
                        u'API :: Found show with indexerid: {0}, however it contained no show name', self.indexerid
                    )
                    return _responds(RESULT_FAILURE, msg='Show contains no name, invalid result')

                # found show
                results = [{INDEXER_IDS[_indexer]: int(my_show.data['id']),
                            'name': text_type(my_show.data['seriesname']),
                            'first_aired': my_show.data['firstaired'],
                            'indexer': int(_indexer)}]
                break

            return _responds(RESULT_SUCCESS, {'results': results, 'langid': lang_id})
        else:
            return _responds(RESULT_FAILURE, msg='Either a unique id or name is required!')


class CMD_SearchTVDB(CMD_SearchIndexers):
    _help = {
        'desc': 'Search for a show with a given name on The TVDB, in a specific language',
        'optionalParameters': {
            'name': {'desc': 'The name of the show you want to search for'},
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'lang': {'desc': 'The 2-letter language code of the desired show'},
        }
    }

    def __init__(self, args, kwargs):
        CMD_SearchIndexers.__init__(self, args, kwargs)
        self.indexerid, args = self.check_params(args, kwargs, 'tvdbid', None, False, 'int', [])


class CMD_SearchTVRAGE(CMD_SearchIndexers):
    """
    Deprecated, TVRage is no more.
    """

    _help = {
        'desc':
            'Search for a show with a given name on TVRage, in a specific language. '
            'This command should not longer be used, as TVRage was shut down.',
        'optionalParameters': {
            'name': {'desc': 'The name of the show you want to search for'},
            'lang': {'desc': 'The 2-letter language code of the desired show'},
        }
    }

    def __init__(self, args, kwargs):
        # Leave this one as APICall so it doesnt try and search anything
        # pylint: disable=non-parent-init-called,super-init-not-called
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        return _responds(RESULT_FAILURE, msg='TVRage is no more, invalid result')


class CMD_SetDefaults(ApiCall):
    _help = {
        'desc': "Set Medusa's user default configuration value",
        'optionalParameters': {
            'initial': {'desc': 'The initial quality of a show'},
            'archive': {'desc': 'The archive quality of a show'},
            'future_show_paused': {'desc': 'True to list paused shows in the coming episode, False otherwise'},
            'season_folders': {'desc': 'True to use season folders for the show, False otherwise'},
            'status': {'desc': 'Status of missing episodes'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.initial, args = self.check_params(args, kwargs, 'initial', None, False, 'list', list(quality_map))
        self.archive, args = self.check_params(args, kwargs, 'archive', None, False, 'list',
                                               list(quality_map).remove('unknown'))
        self.future_show_paused, args = self.check_params(args, kwargs, 'future_show_paused', None, False, 'bool', [])
        self.season_folders, args = self.check_params(args, kwargs, 'flatten_folders',
                                                      not bool(app.SEASON_FOLDERS_DEFAULT), False, 'bool', [])
        self.season_folders, args = self.check_params(args, kwargs, 'season_folders',
                                                      bool(app.SEASON_FOLDERS_DEFAULT), False, 'bool', [])
        self.status, args = self.check_params(args, kwargs, 'status', None, False, 'string',
                                              ['wanted', 'skipped', 'ignored'])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Set Medusa's user default configuration value """

        i_quality_id = []
        a_quality_id = []

        if self.initial:
            for quality in self.initial:
                i_quality_id.append(quality_map[quality])
        if self.archive:
            for quality in self.archive:
                a_quality_id.append(quality_map[quality])

        if i_quality_id or a_quality_id:
            app.QUALITY_DEFAULT = Quality.combine_qualities(i_quality_id, a_quality_id)

        if self.status:
            # convert the string status to a int
            for status in statusStrings:
                if statusStrings[status].lower() == text_type(self.status).lower():
                    self.status = status
                    break
            # this should be obsolete because of the above
            if self.status not in statusStrings:
                raise ApiError('Invalid Status')
            # only allow the status options we want
            if int(self.status) not in (3, 5, 6, 7):
                raise ApiError('Status Prohibited')
            app.STATUS_DEFAULT = self.status

        if self.season_folders is not None:
            app.SEASON_FOLDERS_DEFAULT = int(self.season_folders)

        if self.future_show_paused is not None:
            app.COMING_EPS_DISPLAY_PAUSED = int(self.future_show_paused)

        return _responds(RESULT_SUCCESS, msg='Saved defaults')


class CMD_Shutdown(ApiCall):
    _help = {'desc': 'Shutdown Medusa'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Shutdown Medusa """
        if not Shutdown.stop(app.PID):
            return _responds(RESULT_FAILURE, msg='Medusa can not be shut down')

        return _responds(RESULT_SUCCESS, msg='Medusa is shutting down...')


class CMD_Update(ApiCall):
    _help = {'desc': 'Update Medusa to the latest version available'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        check_version = CheckVersion()

        if check_version.check_for_new_version():
            if check_version.run_backup_if_safe():
                check_version.update()

                return _responds(RESULT_SUCCESS, msg='Medusa is updating ...')

            return _responds(RESULT_FAILURE, msg='Medusa could not backup config ...')

        return _responds(RESULT_FAILURE, msg='Medusa is already up to date')


class CMD_Show(ApiCall):
    _help = {
        'desc': 'Get detailed information about a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get detailed information about a show """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        show_dict = {
            'season_list': CMD_ShowSeasonList((), {'indexerid': self.indexerid}).run()['data'],
            'cache': CMD_ShowCache((), {'indexerid': self.indexerid}).run()['data']
        }

        genre_list = []
        if show_obj.genre:
            genre_list_tmp = show_obj.genre.split('|')
            for genre in genre_list_tmp:
                if genre:
                    genre_list.append(genre)

        show_dict['genre'] = genre_list
        show_dict['quality'] = get_quality_string(show_obj.quality)

        any_qualities, best_qualities = _map_quality(show_obj.quality)
        show_dict['quality_details'] = {'initial': any_qualities, 'archive': best_qualities}

        try:
            show_dict['location'] = show_obj.validate_location
        except ShowDirectoryNotFoundException:
            show_dict['location'] = ''

        show_dict['language'] = show_obj.lang
        show_dict['show_name'] = show_obj.name
        show_dict['paused'] = (0, 1)[show_obj.paused]
        show_dict['subtitles'] = (0, 1)[show_obj.subtitles]
        show_dict['air_by_date'] = (0, 1)[show_obj.air_by_date]
        show_dict['season_folders'] = (0, 1)[show_obj.season_folders]
        show_dict['sports'] = (0, 1)[show_obj.sports]
        show_dict['anime'] = (0, 1)[show_obj.anime]
        show_dict['airs'] = text_type(show_obj.airs).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' ')
        show_dict['dvdorder'] = (0, 1)[show_obj.dvd_order]

        if show_obj.rls_require_words:
            show_dict['rls_require_words'] = show_obj.rls_require_words.split(', ')
        else:
            show_dict['rls_require_words'] = []

        if show_obj.rls_ignore_words:
            show_dict['rls_ignore_words'] = show_obj.rls_ignore_words.split(', ')
        else:
            show_dict['rls_ignore_words'] = []

        show_dict['scene'] = (0, 1)[show_obj.scene]
        # show_dict['archive_firstmatch'] = (0, 1)[show_obj.archive_firstmatch]
        # This might need to be here for 3rd part apps?
        show_dict['archive_firstmatch'] = 1

        show_dict['indexerid'] = show_obj.indexerid
        show_dict['tvdbid'] = show_obj.indexerid if show_obj.indexer == INDEXER_TVDBV2 else \
            show_obj.externals.get('tvdb_id', '')
        show_dict['imdbid'] = show_obj.externals.get('imdb_id', '')

        show_dict['network'] = show_obj.network
        if not show_dict['network']:
            show_dict['network'] = ''
        show_dict['status'] = show_obj.status

        if try_int(show_obj.next_aired, 1) > 693595:
            dt_episode_airs = sbdatetime.sbdatetime.convert_to_setting(
                network_timezones.parse_date_time(show_obj.next_aired, show_dict['airs'], show_dict['network']))
            show_dict['airs'] = sbdatetime.sbdatetime.sbftime(dt_episode_airs, t_preset=timeFormat).lstrip('0').replace(
                ' 0', ' ')
            show_dict['next_ep_airdate'] = sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat)
        else:
            show_dict['next_ep_airdate'] = ''

        return _responds(RESULT_SUCCESS, show_dict)


class CMD_ShowAddExisting(ApiCall):
    _help = {
        'desc': 'Add an existing show in Medusa',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
            'location': {'desc': "Full path to the existing shows's folder"},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'initial': {'desc': 'The initial quality of the show'},
            'archive': {'desc': 'The archive quality of the show'},
            'season_folders': {'desc': 'True to use season folders for the show, False otherwise'},
            'subtitles': {'desc': 'True to search for subtitles, False otherwise'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, '', [])
        self.location, args = self.check_params(args, kwargs, 'location', None, True, 'string', [])
        # optional
        self.initial, args = self.check_params(args, kwargs, 'initial', None, False, 'list', list(quality_map))
        self.archive, args = self.check_params(args, kwargs, 'archive', None, False, 'list',
                                               list(quality_map).remove('unknown'))
        self.season_folders, args = self.check_params(args, kwargs, 'flatten_folders',
                                                      not bool(app.SEASON_FOLDERS_DEFAULT), False, 'bool', [])
        self.season_folders, args = self.check_params(args, kwargs, 'season_folders',
                                                      bool(app.SEASON_FOLDERS_DEFAULT), False, 'bool', [])
        self.subtitles, args = self.check_params(args, kwargs, 'subtitles', int(app.USE_SUBTITLES),
                                                 False, 'int', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Add an existing show in Medusa """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if show_obj:
            return _responds(RESULT_FAILURE, msg='An existing indexerid already exists in the database')

        if not os.path.isdir(self.location):
            return _responds(RESULT_FAILURE, msg='Not a valid location')

        indexer_name = None
        indexer_result = CMD_SearchIndexers([], {INDEXER_IDS[self.indexer]: self.indexerid}).run()

        if indexer_result['result'] == result_type_map[RESULT_SUCCESS]:
            if not indexer_result['data']['results']:
                return _responds(RESULT_FAILURE, msg='Empty results returned, check indexerid and try again')
            if len(indexer_result['data']['results']) == 1 and 'name' in indexer_result['data']['results'][0]:
                indexer_name = indexer_result['data']['results'][0]['name']

        if not indexer_name:
            return _responds(RESULT_FAILURE, msg='Unable to retrieve information from indexer')

        # set indexer so we can pass it along when adding show to Medusa
        indexer = indexer_result['data']['results'][0]['indexer']

        # use default quality as a fail-safe
        new_quality = int(app.QUALITY_DEFAULT)
        i_quality_id = []
        a_quality_id = []

        if self.initial:
            for quality in self.initial:
                i_quality_id.append(quality_map[quality])
        if self.archive:
            for quality in self.archive:
                a_quality_id.append(quality_map[quality])

        if i_quality_id or a_quality_id:
            new_quality = Quality.combine_qualities(i_quality_id, a_quality_id)

        app.show_queue_scheduler.action.addShow(
            int(indexer), int(self.indexerid), self.location,
            default_status=app.STATUS_DEFAULT, quality=new_quality,
            season_folders=int(self.season_folders), subtitles=self.subtitles,
            default_status_after=app.STATUS_DEFAULT_AFTER
        )

        return _responds(RESULT_SUCCESS, {'name': indexer_name}, '{0} has been queued to be added'.format(indexer_name))


class CMD_ShowAddNew(ApiCall):
    _help = {
        'desc': 'Add a new show to Medusa',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'initial': {'desc': 'The initial quality of the show'},
            'location': {'desc': 'The path to the folder where the show should be created'},
            'archive': {'desc': 'The archive quality of the show'},
            'season_folders': {'desc': 'True to use season folders for the show, False otherwise'},
            'status': {'desc': 'The status of missing episodes'},
            'lang': {'desc': 'The 2-letter language code of the desired show'},
            'subtitles': {'desc': 'True to search for subtitles, False otherwise'},
            'anime': {'desc': 'True to mark the show as an anime, False otherwise'},
            'scene': {'desc': 'True if episodes search should be made by scene numbering, False otherwise'},
            'future_status': {'desc': 'The status of future episodes'},
        }
    }

    def __init__(self, args, kwargs):
        self.valid_languages = indexerApi().config['langabbv_to_id']
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        self.location, args = self.check_params(args, kwargs, 'location', None, False, 'string', [])
        self.initial, args = self.check_params(args, kwargs, 'initial', None, False, 'list', list(quality_map))
        self.archive, args = self.check_params(args, kwargs, 'archive', None, False, 'list',
                                               list(quality_map).remove('unknown'))
        self.season_folders, args = self.check_params(args, kwargs, 'flatten_folders',
                                                      not bool(app.SEASON_FOLDERS_DEFAULT), False, 'bool', [])
        self.season_folders, args = self.check_params(args, kwargs, 'season_folders',
                                                      bool(app.SEASON_FOLDERS_DEFAULT), False, 'bool', [])
        self.status, args = self.check_params(args, kwargs, 'status', None, False, 'string',
                                              ['wanted', 'skipped', 'ignored'])
        self.lang, args = self.check_params(args, kwargs, 'lang', app.INDEXER_DEFAULT_LANGUAGE, False, 'string',
                                            list(self.valid_languages))
        self.subtitles, args = self.check_params(args, kwargs, 'subtitles', bool(app.USE_SUBTITLES),
                                                 False, 'bool', [])
        self.anime, args = self.check_params(args, kwargs, 'anime', bool(app.ANIME_DEFAULT), False,
                                             'bool', [])
        self.scene, args = self.check_params(args, kwargs, 'scene', bool(app.SCENE_DEFAULT), False,
                                             'bool', [])
        self.future_status, args = self.check_params(args, kwargs, 'future_status', None, False, 'string',
                                                     ['wanted', 'skipped', 'ignored'])

        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Add a new show to Medusa """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if show_obj:
            return _responds(RESULT_FAILURE, msg='An existing indexerid already exists in database')

        if not self.location:
            if app.ROOT_DIRS:
                log.debug(u'Root directories: {0}', app.ROOT_DIRS)
                root_dirs = app.ROOT_DIRS[1:]
                default_index = int(app.ROOT_DIRS[0])
                self.location = root_dirs[default_index]
                log.debug(u'Default location: {0}', self.location)
            else:
                return _responds(RESULT_FAILURE, msg='Root directory is not set, please provide a location')

        if not os.path.isdir(self.location):
            return _responds(RESULT_FAILURE, msg='{0!r} is not a valid location'.format(self.location))

        # use default quality as a fail-safe
        new_quality = int(app.QUALITY_DEFAULT)
        i_quality_id = []
        a_quality_id = []

        if self.initial:
            for quality in self.initial:
                i_quality_id.append(quality_map[quality])
        if self.archive:
            for quality in self.archive:
                a_quality_id.append(quality_map[quality])

        if i_quality_id or a_quality_id:
            new_quality = Quality.combine_qualities(i_quality_id, a_quality_id)

        # use default status as a fail-safe
        new_status = app.STATUS_DEFAULT
        if self.status:
            # convert the string status to a int
            for status in statusStrings:
                if statusStrings[status].lower() == text_type(self.status).lower():
                    self.status = status
                    break

            if self.status not in statusStrings:
                raise ApiError('Invalid Status')

            # only allow the status options we want
            if int(self.status) not in (WANTED, SKIPPED, IGNORED):
                return _responds(RESULT_FAILURE, msg='Status prohibited')
            new_status = self.status

        # use default status as a fail-safe
        default_ep_status_after = app.STATUS_DEFAULT_AFTER
        if self.future_status:
            # convert the string status to a int
            for status in statusStrings:
                if statusStrings[status].lower() == text_type(self.future_status).lower():
                    self.future_status = status
                    break

            if self.future_status not in statusStrings:
                raise ApiError('Invalid Status')

            # only allow the status options we want
            if int(self.future_status) not in (WANTED, SKIPPED, IGNORED):
                return _responds(RESULT_FAILURE, msg='Status prohibited')
            default_ep_status_after = self.future_status

        indexer_name = None
        indexer_result = CMD_SearchIndexers([], {INDEXER_IDS[self.indexer]: self.indexerid, 'lang': self.lang}).run()

        if indexer_result['result'] == result_type_map[RESULT_SUCCESS]:
            if not indexer_result['data']['results']:
                return _responds(RESULT_FAILURE, msg='Empty results returned, check indexerid and try again')
            if len(indexer_result['data']['results']) == 1 and 'name' in indexer_result['data']['results'][0]:
                indexer_name = indexer_result['data']['results'][0]['name']

        if not indexer_name:
            return _responds(RESULT_FAILURE, msg='Unable to retrieve information from indexer')

        # set indexer for found show so we can pass it along
        indexer = indexer_result['data']['results'][0]['indexer']

        # moved the logic check to the end in an attempt to eliminate empty directory being created from previous errors
        show_path = os.path.join(self.location, sanitize_filename(indexer_name))

        # don't create show dir if config says not to
        if app.ADD_SHOWS_WO_DIR:
            log.info(u'Skipping initial creation of {0} due to config.ini setting', show_path)
        else:
            dir_exists = helpers.make_dir(show_path)
            if not dir_exists:
                log.error(u"API :: Unable to create the folder {0}, can't add the show", show_path)
                return _responds(RESULT_FAILURE, {'path': show_path},
                                 "Unable to create the folder {0}, can't add the show".format(show_path))
            else:
                helpers.chmod_as_parent(show_path)

        app.show_queue_scheduler.action.addShow(
            int(indexer), int(self.indexerid), show_path, default_status=new_status,
            quality=new_quality, season_folders=int(self.season_folders),
            lang=self.lang, subtitles=self.subtitles, anime=self.anime,
            scene=self.scene, default_status_after=default_ep_status_after
        )

        return _responds(RESULT_SUCCESS, {'name': indexer_name}, indexer_name + ' has been queued to be added')


class CMD_ShowCache(ApiCall):
    _help = {
        'desc': "Check Medusa's cache to see if the images (poster, banner, fanart) for a show are valid",
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """Check cache to see if the images for a show are valid."""
        # TODO: Add support for additional types
        series_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not series_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        # TODO: catch if cache dir is missing/invalid.. so it doesn't break show/show.cache
        # return {"poster": 0, "banner": 0}

        image_types = image_cache.IMAGE_TYPES

        results = {
            image_types[img]: 1 if image_cache.get_artwork(img, series_obj) else 0
            for img in image_types
        }

        return _responds(RESULT_SUCCESS, results)


class CMD_ShowDelete(ApiCall):
    _help = {
        'desc': 'Delete a show in Medusa',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'remove_files': {
                'desc': 'True to delete the files associated with the show, False otherwise. This can not be undone!'
            },
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        self.remove_files, args = self.check_params(args, kwargs, 'remove_files', False, False, 'bool', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Delete a show in Medusa """
        error, show = Show.delete(INDEXER_TVDBV2, self.indexerid, self.remove_files)

        if error:
            return _responds(RESULT_FAILURE, msg=error)

        return _responds(RESULT_SUCCESS, msg='{0} has been queued to be deleted'.format(show.name))


class CMD_ShowGetQuality(ApiCall):
    _help = {
        'desc': 'Get the quality setting of a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the quality setting of a show """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        any_qualities, best_qualities = _map_quality(show_obj.quality)

        return _responds(RESULT_SUCCESS, {'initial': any_qualities, 'archive': best_qualities})


class CMD_ShowGetPoster(ApiCall):
    _help = {
        'desc': 'Get the poster of a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the poster a show """
        series_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not series_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')
        return {
            'outputType': 'image',
            'image': ShowPoster(series_obj),
        }


class CMD_ShowGetBanner(ApiCall):
    _help = {
        'desc': 'Get the banner of a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the banner of a show """
        series_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not series_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')
        return {
            'outputType': 'image',
            'image': ShowBanner(series_obj),
        }


class CMD_ShowGetNetworkLogo(ApiCall):
    _help = {
        'desc': 'Get the network logo of a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """
        :return: Get the network logo of a show
        """
        series_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not series_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')
        return {
            'outputType': 'image',
            'image': ShowNetworkLogo(series_obj),
        }


class CMD_ShowGetFanArt(ApiCall):
    _help = {
        'desc': 'Get the fan art of a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the fan art of a show """
        series_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not series_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')
        return {
            'outputType': 'image',
            'image': ShowFanArt(series_obj),
        }


class CMD_ShowPause(ApiCall):
    _help = {
        'desc': 'Pause or un-pause a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'pause': {'desc': 'True to pause the show, False otherwise'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        self.pause, args = self.check_params(args, kwargs, 'pause', False, False, 'bool', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Pause or un-pause a show """
        error, show = Show.pause(INDEXER_TVDBV2, self.indexerid, self.pause)

        if error:
            return _responds(RESULT_FAILURE, msg=error)

        return _responds(RESULT_SUCCESS, msg='{0} has been {1}'.format(show.name, ('resumed', 'paused')[show.paused]))


class CMD_ShowRefresh(ApiCall):
    _help = {
        'desc': 'Refresh a show in Medusa',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Refresh a show in Medusa """
        error, show = Show.refresh(INDEXER_TVDBV2, self.indexerid)

        if error:
            return _responds(RESULT_FAILURE, msg=error)

        return _responds(RESULT_SUCCESS, msg='{0} has queued to be refreshed'.format(show.name))


class CMD_ShowSeasonList(ApiCall):
    _help = {
        'desc': 'Get the list of seasons of a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'sort': {'desc': 'Return the seasons in ascending or descending order'}
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        self.sort, args = self.check_params(args, kwargs, 'sort', 'desc', False, 'string', ['asc', 'desc'])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the list of seasons of a show """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        main_db_con = db.DBConnection()
        if self.sort == 'asc':
            sql_results = main_db_con.select(
                'SELECT DISTINCT season FROM tv_episodes WHERE indexer = ? AND showid = ? ORDER BY season ASC',
                [INDEXER_TVDBV2, self.indexerid])
        else:
            sql_results = main_db_con.select(
                'SELECT DISTINCT season FROM tv_episodes WHERE indexer = ? AND showid = ? ORDER BY season DESC',
                [INDEXER_TVDBV2, self.indexerid])
        season_list = []  # a list with all season numbers
        for row in sql_results:
            season_list.append(int(row['season']))

        return _responds(RESULT_SUCCESS, season_list)


class CMD_ShowSeasons(ApiCall):
    _help = {
        'desc': 'Get the list of episodes for one or all seasons of a show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'season': {'desc': 'The season number'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        self.season, args = self.check_params(args, kwargs, 'season', None, False, 'int', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the list of episodes for one or all seasons of a show """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        main_db_con = db.DBConnection()

        if self.season is None:
            sql_results = main_db_con.select(
                'SELECT name, episode, airdate, status, quality, release_name, season, location, file_size, subtitles '
                'FROM tv_episodes WHERE indexer = ? AND showid = ?',
                [INDEXER_TVDBV2, self.indexerid])
            seasons = {}
            for row in sql_results:
                status, quality = int(row['status']), int(row['quality'])
                row['status'] = statusStrings[status]
                row['quality'] = get_quality_string(quality)
                if try_int(row['airdate'], 1) > 693595:  # 1900
                    dt_episode_airs = sbdatetime.sbdatetime.convert_to_setting(
                        network_timezones.parse_date_time(row['airdate'], show_obj.airs, show_obj.network))
                    row['airdate'] = sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat)
                else:
                    row['airdate'] = 'Never'
                cur_season = int(row['season'])
                cur_episode = int(row['episode'])
                del row['season']
                del row['episode']
                if cur_season not in seasons:
                    seasons[cur_season] = {}
                seasons[cur_season][cur_episode] = row

        else:
            sql_results = main_db_con.select(
                'SELECT name, episode, airdate, status, quality, location, file_size, release_name, subtitles'
                ' FROM tv_episodes WHERE indexer = ? AND showid = ? AND season = ?',
                [INDEXER_TVDBV2, self.indexerid, self.season])
            if not sql_results:
                return _responds(RESULT_FAILURE, msg='Season not found')
            seasons = {}
            for row in sql_results:
                cur_episode = int(row['episode'])
                del row['episode']
                status, quality = int(row['status']), int(row['quality'])
                row['status'] = statusStrings[status]
                row['quality'] = get_quality_string(quality)
                if try_int(row['airdate'], 1) > 693595:  # 1900
                    dt_episode_airs = sbdatetime.sbdatetime.convert_to_setting(
                        network_timezones.parse_date_time(row['airdate'], show_obj.airs, show_obj.network))
                    row['airdate'] = sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat)
                else:
                    row['airdate'] = 'Never'
                if cur_episode not in seasons:
                    seasons[cur_episode] = {}
                seasons[cur_episode] = row

        return _responds(RESULT_SUCCESS, seasons)


class CMD_ShowSetQuality(ApiCall):
    _help = {
        'desc': 'Set the quality setting of a show. If no quality is provided, the default user setting is used.',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
            'initial': {'desc': 'The initial quality of the show'},
            'archive': {'desc': 'The archive quality of the show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        self.initial, args = self.check_params(args, kwargs, 'initial', None, False, 'list', list(quality_map))
        self.archive, args = self.check_params(args, kwargs, 'archive', None, False, 'list',
                                               list(quality_map).remove('unknown'))
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Set the quality setting of a show. If no quality is provided, the default user setting is used. """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        # use default quality as a fail-safe
        new_quality = int(app.QUALITY_DEFAULT)
        i_quality_id = []
        a_quality_id = []

        if self.initial:
            for quality in self.initial:
                i_quality_id.append(quality_map[quality])
        if self.archive:
            for quality in self.archive:
                a_quality_id.append(quality_map[quality])

        if i_quality_id or a_quality_id:
            new_quality = Quality.combine_qualities(i_quality_id, a_quality_id)
        show_obj.quality = new_quality

        return _responds(RESULT_SUCCESS,
                         msg='{0} quality has been changed to {1}'.format(show_obj.name, get_quality_string(show_obj.quality)))


class CMD_ShowStats(ApiCall):
    _help = {
        'desc': 'Get episode statistics for a given show',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get episode statistics for a given show """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        # show stats
        episode_status_counts_total = {'total': 0}
        for status_code in statusStrings:
            if status_code not in (UNSET, DOWNLOADED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, ARCHIVED):
                episode_status_counts_total[status_code] = 0

        # add all the downloaded qualities
        episode_qualities_counts_download = {'total': 0}
        for status_code in (DOWNLOADED, ARCHIVED):
            episode_qualities_counts_download[status_code] = {}

        # add all snatched qualities
        episode_qualities_counts_snatch = {'total': 0}
        for status_code in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST):
            episode_qualities_counts_snatch[status_code] = {}

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select('SELECT status, quality, season FROM tv_episodes '
                                         'WHERE season != 0 AND indexer = ? AND showid = ?',
                                         [INDEXER_TVDBV2, self.indexerid])

        # the main loop that goes through all episodes
        for row in sql_results:
            status, quality = int(row['status']), int(row['quality'])

            episode_status_counts_total['total'] += 1

            if status in (DOWNLOADED, ARCHIVED):
                episode_qualities_counts_download['total'] += 1
                if quality not in episode_qualities_counts_download[status]:
                    episode_qualities_counts_download[status][quality] = 1
                else:
                    episode_qualities_counts_download[status][quality] += 1
            elif status in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST):
                episode_qualities_counts_snatch['total'] += 1
                if quality not in episode_qualities_counts_snatch[status]:
                    episode_qualities_counts_snatch[status][quality] = 1
                else:
                    episode_qualities_counts_snatch[status][quality] += 1
            elif status not in (UNSET, ):
                episode_status_counts_total[status] += 1

        # the outgoing container
        episodes_stats = {'downloaded': {}}
        # turning codes into strings
        for status in episode_qualities_counts_download:
            if status == 'total':
                episodes_stats['downloaded']['total'] = episode_qualities_counts_download[status]
                continue
            for quality in episode_qualities_counts_download[status]:
                quality_string = Quality.qualityStrings[quality].lower().replace(' ', '_')
                if quality_string not in episodes_stats['downloaded']:
                    episodes_stats['downloaded'][quality_string] = episode_qualities_counts_download[status][quality]
                else:
                    episodes_stats['downloaded'][quality_string] += episode_qualities_counts_download[status][quality]

        episodes_stats['snatched'] = {}
        for status in episode_qualities_counts_snatch:
            if status == 'total':
                episodes_stats['snatched']['total'] = episode_qualities_counts_snatch[status]
                continue
            for quality in episode_qualities_counts_snatch[status]:
                quality_string = Quality.qualityStrings[quality].lower().replace(' ', '_')
                if quality_string not in episodes_stats['snatched']:
                    episodes_stats['snatched'][quality_string] = episode_qualities_counts_snatch[status][quality]
                else:
                    episodes_stats['snatched'][quality_string] += episode_qualities_counts_snatch[status][quality]

        for status in episode_status_counts_total:
            if status == 'total':
                episodes_stats['total'] = episode_status_counts_total[status]
                continue
            status_string = statusStrings[status].lower().replace(' ', '_').replace('(', '').replace(')', '')
            episodes_stats[status_string] = episode_status_counts_total[status]

        return _responds(RESULT_SUCCESS, episodes_stats)


class CMD_ShowUpdate(ApiCall):
    _help = {
        'desc': 'Update a show in Medusa',
        'requiredParameters': {
            'indexerid': {'desc': 'Unique ID of a show'},
        },
        'optionalParameters': {
            'tvdbid': {'desc': 'thetvdb.com unique ID of a show'},
        }
    }

    def __init__(self, args, kwargs):
        # required
        self.indexerid, args = self.check_params(args, kwargs, 'indexerid', None, True, 'int', [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Update a show in Medusa """
        show_obj = Show.find_by_id(app.showList, INDEXER_TVDBV2, self.indexerid)
        if not show_obj:
            return _responds(RESULT_FAILURE, msg='Show not found')

        try:
            app.show_queue_scheduler.action.updateShow(show_obj)
            return _responds(RESULT_SUCCESS, msg='{0} has queued to be updated'.format(show_obj.name))
        except CantUpdateShowException as error:
            log.debug(u'API::Unable to update show: {0!r}', error)
            return _responds(RESULT_FAILURE, msg='Unable to update {0}'.format(show_obj.name))


class CMD_Shows(ApiCall):
    _help = {
        'desc': 'Get all shows in Medusa',
        'optionalParameters': {
            'sort': {'desc': 'The sorting strategy to apply to the list of shows'},
            'paused': {'desc': 'True: show paused, False: show un-paused, otherwise show all'},
        },
    }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.sort, args = self.check_params(args, kwargs, 'sort', 'id', False, 'string', ['id', 'name'])
        self.paused, args = self.check_params(args, kwargs, 'paused', None, False, 'bool', [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get all shows in Medusa """
        shows = {}
        for cur_show in app.showList:
            # If self.paused is None: show all, 0: show un-paused, 1: show paused
            if self.paused is not None and self.paused != cur_show.paused:
                continue

            if cur_show.indexer != INDEXER_TVDBV2:
                continue

            show_dict = {
                'paused': (0, 1)[cur_show.paused],
                'quality': get_quality_string(cur_show.quality),
                'language': cur_show.lang,
                'air_by_date': (0, 1)[cur_show.air_by_date],
                'sports': (0, 1)[cur_show.sports],
                'anime': (0, 1)[cur_show.anime],
                'indexerid': cur_show.indexerid,
                'tvdbid': cur_show.indexerid if cur_show.indexer == INDEXER_TVDBV2
                else cur_show.externals.get('tvdb_id', ''),
                'network': cur_show.network,
                'show_name': cur_show.name,
                'status': cur_show.status,
                'subtitles': (0, 1)[cur_show.subtitles],
            }

            if try_int(cur_show.next_aired, 1) > 693595:  # 1900
                dt_episode_airs = sbdatetime.sbdatetime.convert_to_setting(
                    network_timezones.parse_date_time(cur_show.next_aired, cur_show.airs, show_dict['network']))
                show_dict['next_ep_airdate'] = sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat)
            else:
                show_dict['next_ep_airdate'] = ''

            show_dict['cache'] = CMD_ShowCache((), {'indexerid': cur_show.indexerid}).run()['data']
            if not show_dict['network']:
                show_dict['network'] = ''
            if self.sort == 'name':
                shows[cur_show.name] = show_dict
            else:
                shows[cur_show.indexerid] = show_dict

        return _responds(RESULT_SUCCESS, shows)


class CMD_ShowsStats(ApiCall):
    _help = {'desc': 'Get the global shows and episodes statistics'}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ Get the global shows and episodes statistics """
        stats = Show.overall_stats()

        return _responds(RESULT_SUCCESS, {
            'ep_downloaded': stats['episodes']['downloaded'],
            'ep_snatched': stats['episodes']['snatched'],
            'ep_total': stats['episodes']['total'],
            'shows_active': stats['shows']['active'],
            'shows_total': stats['shows']['total'],
        })


# WARNING: never define a cmd call string that contains a "_" (underscore)
# this is reserved for cmd indexes used while cmd chaining

# WARNING: never define a param name that contains a "." (dot)
# this is reserved for cmd namespaces used while cmd chaining
function_mapper = {
    'help': CMD_Help,
    'future': CMD_ComingEpisodes,
    'episode': CMD_Episode,
    'episode.search': CMD_EpisodeSearch,
    'episode.setstatus': CMD_EpisodeSetStatus,
    'episode.subtitlesearch': CMD_SubtitleSearch,
    'exceptions': CMD_Exceptions,
    'history': CMD_History,
    'history.clear': CMD_HistoryClear,
    'history.trim': CMD_HistoryTrim,
    'failed': CMD_Failed,
    'backlog': CMD_Backlog,
    'logs': CMD_Logs,
    'logs.clear': CMD_LogsClear,
    'sb': CMD_,
    'postprocess': CMD_PostProcess,
    'sb.addrootdir': CMD_AddRootDir,
    'sb.checkversion': CMD_CheckVersion,
    'sb.checkscheduler': CMD_CheckScheduler,
    'sb.deleterootdir': CMD_DeleteRootDir,
    'sb.getdefaults': CMD_GetDefaults,
    'sb.getmessages': CMD_GetMessages,
    'sb.getrootdirs': CMD_GetRootDirs,
    'sb.pausebacklog': CMD_PauseBacklog,
    'sb.ping': CMD_Ping,
    'sb.restart': CMD_Restart,
    'sb.searchindexers': CMD_SearchIndexers,
    'sb.searchtvdb': CMD_SearchTVDB,
    'sb.searchtvrage': CMD_SearchTVRAGE,
    'sb.setdefaults': CMD_SetDefaults,
    'sb.update': CMD_Update,
    'sb.shutdown': CMD_Shutdown,
    'show': CMD_Show,
    'show.addexisting': CMD_ShowAddExisting,
    'show.addnew': CMD_ShowAddNew,
    'show.cache': CMD_ShowCache,
    'show.delete': CMD_ShowDelete,
    'show.getquality': CMD_ShowGetQuality,
    'show.getposter': CMD_ShowGetPoster,
    'show.getbanner': CMD_ShowGetBanner,
    'show.getnetworklogo': CMD_ShowGetNetworkLogo,
    'show.getfanart': CMD_ShowGetFanArt,
    'show.pause': CMD_ShowPause,
    'show.refresh': CMD_ShowRefresh,
    'show.seasonlist': CMD_ShowSeasonList,
    'show.seasons': CMD_ShowSeasons,
    'show.setquality': CMD_ShowSetQuality,
    'show.stats': CMD_ShowStats,
    'show.update': CMD_ShowUpdate,
    'shows': CMD_Shows,
    'shows.stats': CMD_ShowsStats
}
