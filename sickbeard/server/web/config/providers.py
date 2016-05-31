# coding=utf-8

"""
Configure Providers
"""

from __future__ import unicode_literals

import json
import os
from tornado.routes import route
import sickbeard
from sickbeard import (
    config, logger, ui,
)
from sickbeard.providers import newznab, rsstorrent
from sickrage.helper.common import try_int
from sickrage.helper.encoding import ek
from sickrage.providers.GenericProvider import GenericProvider
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.config.handler import Config


@route('/config/providers(/?.*)')
class ConfigProviders(Config):
    """
    Handler for Provider configuration
    """

    def __init__(self, *args, **kwargs):
        super(ConfigProviders, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the Provider configuration page
        """
        t = PageTemplate(rh=self, filename='config_providers.mako')

        return t.render(submenu=self.ConfigMenu(), title='Config - Providers',
                        header='Search Providers', topmenu='config',
                        controller='config', action='providers')

    @staticmethod
    def canAddNewznabProvider(name):
        """
        See if a Newznab provider can be added
        """

        if not name:
            return json.dumps({'error': 'No Provider Name specified'})

        provider_dict = dict(zip([x.get_id() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        temp_provider = newznab.NewznabProvider(name, '')

        if temp_provider.get_id() in provider_dict:
            return json.dumps({'error': 'Provider Name already exists as {name}'.format(name=provider_dict[temp_provider.get_id()].name)})
        else:
            return json.dumps({'success': temp_provider.get_id()})

    @staticmethod
    def saveNewznabProvider(name, url, key=''):
        """
        Save a Newznab Provider
        """

        if not name or not url:
            return '0'

        provider_dict = dict(zip([x.name for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        if name in provider_dict:
            if not provider_dict[name].default:
                provider_dict[name].name = name
                provider_dict[name].url = config.clean_url(url)

            provider_dict[name].key = key
            # a 0 in the key spot indicates that no key is needed
            if key == '0':
                provider_dict[name].needs_auth = False
            else:
                provider_dict[name].needs_auth = True

            return '|'.join([provider_dict[name].get_id(), provider_dict[name].configStr()])

        else:
            new_provider = newznab.NewznabProvider(name, url, key=key)
            sickbeard.newznabProviderList.append(new_provider)
            return '|'.join([new_provider.get_id(), new_provider.configStr()])

    @staticmethod
    def getNewznabCategories(name, url, key):
        """
        Retrieves a list of possible categories with category id's
        Using the default url/api?cat
        http://yournewznaburl.com/api?t=caps&apikey=yourapikey
        """
        error = ''

        if not name:
            error += '\nNo Provider Name specified'
        if not url:
            error += '\nNo Provider Url specified'
        if not key:
            error += '\nNo Provider Api key specified'

        if error != '':
            return json.dumps({'success': False, 'error': error})

        # Get list with Newznabproviders
        # providerDict = dict(zip([x.get_id() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        # Get newznabprovider obj with provided name
        temp_provider = newznab.NewznabProvider(name, url, key)

        success, tv_categories, error = temp_provider.get_newznab_categories()

        return json.dumps({'success': success, 'tv_categories': tv_categories, 'error': error})

    @staticmethod
    def deleteNewznabProvider(nnid):
        """
        Delete a Newznab Provider
        """

        provider_dict = dict(zip([x.get_id() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        if nnid not in provider_dict or provider_dict[nnid].default:
            return '0'

        # delete it from the list
        sickbeard.newznabProviderList.remove(provider_dict[nnid])

        if nnid in sickbeard.PROVIDER_ORDER:
            sickbeard.PROVIDER_ORDER.remove(nnid)

        return '1'

    @staticmethod
    def canAddTorrentRssProvider(name, url, cookies, titleTAG):
        """
        See if a Torrent provider can be added
        """
        if not name:
            return json.dumps({'error': 'Invalid name specified'})

        provider_dict = dict(
            zip([x.get_id() for x in sickbeard.torrentRssProviderList], sickbeard.torrentRssProviderList))

        temp_provider = rsstorrent.TorrentRssProvider(name, url, cookies, titleTAG)

        if temp_provider.get_id() in provider_dict:
            return json.dumps({'error': 'Exists as {name}'.format(name=provider_dict[temp_provider.get_id()].name)})
        else:
            (succ, err_msg) = temp_provider.validateRSS()
            if succ:
                return json.dumps({'success': temp_provider.get_id()})
            else:
                return json.dumps({'error': err_msg})

    @staticmethod
    def saveTorrentRssProvider(name, url, cookies, titleTAG):
        """
        Save a Torrent Provider
        """

        if not name or not url:
            return '0'

        provider_dict = dict(zip([x.name for x in sickbeard.torrentRssProviderList], sickbeard.torrentRssProviderList))

        if name in provider_dict:
            provider_dict[name].name = name
            provider_dict[name].url = config.clean_url(url)
            provider_dict[name].cookies = cookies
            provider_dict[name].titleTAG = titleTAG

            return '|'.join([provider_dict[name].get_id(), provider_dict[name].configStr()])

        else:
            new_provider = rsstorrent.TorrentRssProvider(name, url, cookies, titleTAG)
            sickbeard.torrentRssProviderList.append(new_provider)
            return '|'.join([new_provider.get_id(), new_provider.configStr()])

    @staticmethod
    def deleteTorrentRssProvider(id):
        """
        Delete a Torrent Provider
        """
        provider_dict = dict(
            zip([x.get_id() for x in sickbeard.torrentRssProviderList], sickbeard.torrentRssProviderList))

        if id not in provider_dict:
            return '0'

        # delete it from the list
        sickbeard.torrentRssProviderList.remove(provider_dict[id])

        if id in sickbeard.PROVIDER_ORDER:
            sickbeard.PROVIDER_ORDER.remove(id)

        return '1'

    def saveProviders(self, newznab_string='', torrentrss_string='', provider_order=None, **kwargs):
        """
        Save Provider related settings
        """
        results = []

        provider_str_list = provider_order.split()
        provider_list = []

        newznab_provider_dict = dict(
            zip([x.get_id() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        finished_names = []

        # add all the newznab info we got into our list
        if newznab_string:
            for curNewznabProviderStr in newznab_string.split('!!!'):

                if not curNewznabProviderStr:
                    continue

                cur_name, cur_url, cur_key, cur_cat = curNewznabProviderStr.split('|')
                cur_url = config.clean_url(cur_url)

                new_provider = newznab.NewznabProvider(cur_name, cur_url, key=cur_key, catIDs=cur_cat)

                cur_id = new_provider.get_id()

                # if it already exists then update it
                if cur_id in newznab_provider_dict:
                    newznab_provider_dict[cur_id].name = cur_name
                    newznab_provider_dict[cur_id].url = cur_url
                    newznab_provider_dict[cur_id].key = cur_key
                    newznab_provider_dict[cur_id].catIDs = cur_cat
                    # a 0 in the key spot indicates that no key is needed
                    if cur_key == '0':
                        newznab_provider_dict[cur_id].needs_auth = False
                    else:
                        newznab_provider_dict[cur_id].needs_auth = True

                    try:
                        newznab_provider_dict[cur_id].search_mode = str(kwargs['{id}_search_mode'.format(id=cur_id)]).strip()
                    except (AttributeError, KeyError):
                        pass  # these exceptions are actually catching unselected checkboxes

                    try:
                        newznab_provider_dict[cur_id].search_fallback = config.checkbox_to_value(
                            kwargs['{id}_search_fallback'.format(id=cur_id)])
                    except (AttributeError, KeyError):
                        newznab_provider_dict[cur_id].search_fallback = 0  # these exceptions are actually catching unselected checkboxes

                    try:
                        newznab_provider_dict[cur_id].enable_daily = config.checkbox_to_value(
                            kwargs['{id}_enable_daily'.format(id=cur_id)])
                    except (AttributeError, KeyError):
                        newznab_provider_dict[cur_id].enable_daily = 0  # these exceptions are actually catching unselected checkboxes

                    try:
                        newznab_provider_dict[cur_id].enable_manualsearch = config.checkbox_to_value(
                            kwargs['{id}_enable_manualsearch'.format(id=cur_id)])
                    except (AttributeError, KeyError):
                        newznab_provider_dict[cur_id].enable_manualsearch = 0  # these exceptions are actually catching unselected checkboxes

                    try:
                        newznab_provider_dict[cur_id].enable_backlog = config.checkbox_to_value(
                            kwargs['{id}_enable_backlog'.format(id=cur_id)])
                    except (AttributeError, KeyError):
                        newznab_provider_dict[cur_id].enable_backlog = 0  # these exceptions are actually catching unselected checkboxes
                else:
                    sickbeard.newznabProviderList.append(new_provider)

                finished_names.append(cur_id)

        # delete anything that is missing
        for cur_provider in sickbeard.newznabProviderList:
            if cur_provider.get_id() not in finished_names:
                sickbeard.newznabProviderList.remove(cur_provider)

        torrent_rss_provider_dict = dict(
            zip([x.get_id() for x in sickbeard.torrentRssProviderList], sickbeard.torrentRssProviderList))
        finished_names = []

        if torrentrss_string:
            for curTorrentRssProviderStr in torrentrss_string.split('!!!'):

                if not curTorrentRssProviderStr:
                    continue

                cur_name, cur_url, cur_cookies, cur_title_tag = curTorrentRssProviderStr.split('|')
                cur_url = config.clean_url(cur_url)

                new_provider = rsstorrent.TorrentRssProvider(cur_name, cur_url, cur_cookies, cur_title_tag)

                cur_id = new_provider.get_id()

                # if it already exists then update it
                if cur_id in torrent_rss_provider_dict:
                    torrent_rss_provider_dict[cur_id].name = cur_name
                    torrent_rss_provider_dict[cur_id].url = cur_url
                    torrent_rss_provider_dict[cur_id].cookies = cur_cookies
                    torrent_rss_provider_dict[cur_id].curTitleTAG = cur_title_tag
                else:
                    sickbeard.torrentRssProviderList.append(new_provider)

                finished_names.append(cur_id)

        # delete anything that is missing
        for cur_provider in sickbeard.torrentRssProviderList:
            if cur_provider.get_id() not in finished_names:
                sickbeard.torrentRssProviderList.remove(cur_provider)

        disabled_list = []
        # do the enable/disable
        for cur_providerStr in provider_str_list:
            cur_provider, cur_enabled = cur_providerStr.split(':')
            cur_enabled = try_int(cur_enabled)

            cur_prov_obj = [x for x in sickbeard.providers.sortedProviderList() if
                            x.get_id() == cur_provider and hasattr(x, 'enabled')]
            if cur_prov_obj:
                cur_prov_obj[0].enabled = bool(cur_enabled)

            if cur_enabled:
                provider_list.append(cur_provider)
            else:
                disabled_list.append(cur_provider)

            if cur_provider in newznab_provider_dict:
                newznab_provider_dict[cur_provider].enabled = bool(cur_enabled)
            elif cur_provider in torrent_rss_provider_dict:
                torrent_rss_provider_dict[cur_provider].enabled = bool(cur_enabled)

        provider_list.extend(disabled_list)

        # dynamically load provider settings
        for curTorrentProvider in [prov for prov in sickbeard.providers.sortedProviderList() if
                                   prov.provider_type == GenericProvider.TORRENT]:

            if hasattr(curTorrentProvider, 'custom_url'):
                try:
                    curTorrentProvider.custom_url = str(kwargs['{id}_custom_url'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.custom_url = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'minseed'):
                try:
                    curTorrentProvider.minseed = int(str(kwargs['{id}_minseed'.format(id=curTorrentProvider.get_id())]).strip())
                except (AttributeError, KeyError):
                    curTorrentProvider.minseed = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'minleech'):
                try:
                    curTorrentProvider.minleech = int(str(kwargs['{id}_minleech'.format(id=curTorrentProvider.get_id())]).strip())
                except (AttributeError, KeyError):
                    curTorrentProvider.minleech = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'ratio'):
                try:
                    ratio = float(str(kwargs['{id}_ratio'.format(id=curTorrentProvider.get_id())]).strip())
                    curTorrentProvider.ratio = (ratio, -1)[ratio < 0]
                except (AttributeError, KeyError, ValueError):
                    curTorrentProvider.ratio = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'digest'):
                try:
                    curTorrentProvider.digest = str(kwargs['{id}_digest'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.digest = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'hash'):
                try:
                    curTorrentProvider.hash = str(kwargs['{id}_hash'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.hash = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'api_key'):
                try:
                    curTorrentProvider.api_key = str(kwargs['{id}_api_key'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.api_key = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'username'):
                try:
                    curTorrentProvider.username = str(kwargs['{id}_username'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.username = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'password'):
                try:
                    curTorrentProvider.password = str(kwargs['{id}_password'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.password = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'passkey'):
                try:
                    curTorrentProvider.passkey = str(kwargs['{id}_passkey'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.passkey = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'pin'):
                try:
                    curTorrentProvider.pin = str(kwargs['{id}_pin'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.pin = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'confirmed'):
                try:
                    curTorrentProvider.confirmed = config.checkbox_to_value(
                        kwargs['{id}_confirmed'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.confirmed = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'ranked'):
                try:
                    curTorrentProvider.ranked = config.checkbox_to_value(
                        kwargs['{id}_ranked'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.ranked = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'engrelease'):
                try:
                    curTorrentProvider.engrelease = config.checkbox_to_value(
                        kwargs['{id}_engrelease'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.engrelease = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'onlyspasearch'):
                try:
                    curTorrentProvider.onlyspasearch = config.checkbox_to_value(
                        kwargs['{id}_onlyspasearch'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.onlyspasearch = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'sorting'):
                try:
                    curTorrentProvider.sorting = str(kwargs['{id}_sorting'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.sorting = 'seeders'  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'freeleech'):
                try:
                    curTorrentProvider.freeleech = config.checkbox_to_value(
                        kwargs['{id}_freeleech'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.freeleech = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'search_mode'):
                try:
                    curTorrentProvider.search_mode = str(kwargs['{id}_search_mode'.format(id=curTorrentProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.search_mode = 'eponly'  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'search_fallback'):
                try:
                    curTorrentProvider.search_fallback = config.checkbox_to_value(
                        kwargs['{id}_search_fallback'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.search_fallback = 0  # these exceptions are catching unselected checkboxes

            if hasattr(curTorrentProvider, 'enable_daily'):
                try:
                    curTorrentProvider.enable_daily = config.checkbox_to_value(
                        kwargs['{id}_enable_daily'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.enable_daily = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'enable_manualsearch'):
                try:
                    curTorrentProvider.enable_manualsearch = config.checkbox_to_value(
                        kwargs['{id}_enable_manualsearch'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.enable_manualsearch = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'enable_backlog'):
                try:
                    curTorrentProvider.enable_backlog = config.checkbox_to_value(
                        kwargs['{id}_enable_backlog'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.enable_backlog = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'cat'):
                try:
                    curTorrentProvider.cat = int(str(kwargs['{id}_cat'.format(id=curTorrentProvider.get_id())]).strip())
                except (AttributeError, KeyError):
                    curTorrentProvider.cat = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'subtitle'):
                try:
                    curTorrentProvider.subtitle = config.checkbox_to_value(
                        kwargs['{id}_subtitle'.format(id=curTorrentProvider.get_id())])
                except (AttributeError, KeyError):
                    curTorrentProvider.subtitle = 0  # these exceptions are actually catching unselected checkboxes

        for curNzbProvider in [prov for prov in sickbeard.providers.sortedProviderList() if
                               prov.provider_type == GenericProvider.NZB]:

            if hasattr(curNzbProvider, 'api_key'):
                try:
                    curNzbProvider.api_key = str(kwargs['{id}_api_key'.format(id=curNzbProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curNzbProvider.api_key = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'username'):
                try:
                    curNzbProvider.username = str(kwargs['{id}_username'.format(id=curNzbProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curNzbProvider.username = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'search_mode'):
                try:
                    curNzbProvider.search_mode = str(kwargs['{id}_search_mode'.format(id=curNzbProvider.get_id())]).strip()
                except (AttributeError, KeyError):
                    curNzbProvider.search_mode = 'eponly'  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'search_fallback'):
                try:
                    curNzbProvider.search_fallback = config.checkbox_to_value(
                        kwargs['{id}_search_fallback'.format(id=curNzbProvider.get_id())])
                except (AttributeError, KeyError):
                    curNzbProvider.search_fallback = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'enable_daily'):
                try:
                    curNzbProvider.enable_daily = config.checkbox_to_value(
                        kwargs['{id}_enable_daily'.format(id=curNzbProvider.get_id())])
                except (AttributeError, KeyError):
                    curNzbProvider.enable_daily = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'enable_manualsearch'):
                try:
                    curNzbProvider.enable_manualsearch = config.checkbox_to_value(
                        kwargs['{id}_enable_manualsearch'.format(id=curNzbProvider.get_id())])
                except (AttributeError, KeyError):
                    curNzbProvider.enable_manualsearch = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'enable_backlog'):
                try:
                    curNzbProvider.enable_backlog = config.checkbox_to_value(
                        kwargs['{id}_enable_backlog'.format(id=curNzbProvider.get_id())])
                except (AttributeError, KeyError):
                    curNzbProvider.enable_backlog = 0  # these exceptions are actually catching unselected checkboxes

        sickbeard.NEWZNAB_DATA = '!!!'.join([x.configStr() for x in sickbeard.newznabProviderList])
        sickbeard.PROVIDER_ORDER = provider_list

        sickbeard.save_config()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect('/config/providers/')
