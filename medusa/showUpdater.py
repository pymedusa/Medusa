# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

import datetime
import logging
import threading
import time
import xml.etree.ElementTree as ET

import medusa as sickbeard
from . import db, failed_history, helpers, network_timezones, ui
from .helper.exceptions import CantRefreshShowException, CantUpdateShowException
from .indexers.indexer_config import INDEXER_TVDB, INDEXER_TVRAGE

logger = logging.getLogger(__name__)


class ShowUpdater(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.amActive = False
        self.session = helpers.make_session()

    def run(self, force=False):

        self.amActive = True

        bad_indexer = [INDEXER_TVRAGE]
        update_datetime = datetime.datetime.now()
        update_date = update_datetime.date()

        # update_timestamp = calendar.timegm(update_datetime.timetuple())
        update_timestamp = time.mktime(update_datetime.timetuple())
        cache_db_con = db.DBConnection('cache.db')
        result = cache_db_con.select("SELECT `time` FROM lastUpdate WHERE provider = 'theTVDB'")
        if result:
            last_update = int(result[0]['time'])
        else:
            last_update = update_timestamp - 86400
            cache_db_con.action("INSERT INTO lastUpdate (provider,`time`) VALUES (?, ?)", ['theTVDB', last_update])

        # refresh network timezones
        network_timezones.update_network_dict()

        # sure, why not?
        if sickbeard.USE_FAILED_DOWNLOADS:
            failed_history.trimHistory()

        update_delta = update_timestamp - last_update

        if update_delta >= 691200:      # 8 days ( 7 days + 1 day of buffer time)
            update_file = 'updates_month.xml'
        elif update_delta >= 90000:     # 25 hours ( 1 day + 1 hour of buffer time)
            update_file = 'updates_week.xml'
        else:
            update_file = 'updates_day.xml'

        # url = 'http://thetvdb.com/api/Updates.php?type=series&time=%s' % last_update
        url = 'http://thetvdb.com/api/{0}/updates/{1}'.format(sickbeard.indexerApi(INDEXER_TVDB).api_params['apikey'], update_file)
        data = helpers.getURL(url, session=self.session, returns='text')
        if not data:
            logger.info(u'Could not get the recently updated show data from {indexer}. Retrying later. Url was: {logurl}', indexer=sickbeard.indexerApi(INDEXER_TVDB).name, logurl=url)
            self.amActive = False
            return

        updated_shows = []
        try:
            tree = ET.fromstring(data)
            for show in tree.findall("Series"):
                updated_shows.append(int(show.find('id').text))
        except SyntaxError:
            pass

        logger.info(u'Doing full update on all shows')

        pi_list = []
        for cur_show in sickbeard.showList:

            if cur_show.indexer in bad_indexer:
                logger.warning(u'Indexer is no longer available for show [ {show} ] ', show=cur_show.name)
            else:
                indexer_name = sickbeard.indexerApi(cur_show.indexer).name

            try:
                if indexer_name == 'theTVDB':
                    if cur_show.indexerid in updated_shows:
                        # If the cur_show is not 'paused' then add to the showQueueSchedular
                        if not cur_show.paused:
                            pi_list.append(sickbeard.showQueueScheduler.action.updateShow(cur_show))
                        else:
                            logger.info(u'Show update skipped, show: {show} is paused.', show=cur_show.name)
                else:
                    cur_show.next_episode()

                    if cur_show.should_update(update_date=update_date):
                        try:
                            pi_list.append(sickbeard.showQueueScheduler.action.updateShow(cur_show))
                        except CantUpdateShowException as e:
                            logger.debug(u'Unable to update show: {error}', error=e)
                    else:
                        logger.debug(
                            u'Not updating episodes for show {show} because the last or next episode is not within the grace period.', show = cur_show.name)
            except (CantUpdateShowException, CantRefreshShowException) as e:
                logger.warning(u'Automatic update failed. Error: {error}', error=e)
            except Exception as e:
                logger.error(u'Automatic update failed: Error: {error}', error=e)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", pi_list))

        cache_db_con.action("UPDATE lastUpdate SET `time` = ? WHERE provider=?", [update_timestamp, 'theTVDB'])

        logger.info(u'Completed full update on all shows')

        self.amActive = False

    def __del__(self):
        pass
