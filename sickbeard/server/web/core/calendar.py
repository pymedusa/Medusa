# coding=utf-8

"""
iCalendar (iCal) - Standard RFC 5545 <http://tools.ietf.org/html/rfc5546>
Works with iCloud, Google Calendar and Outlook.
"""

from __future__ import unicode_literals

import datetime
from dateutil import tz
from tornado.web import authenticated
import sickbeard
from sickbeard import (
    db, logger, network_timezones,
)
from sickrage.helper.common import try_int
from sickbeard.server.web.core.base import BaseHandler


class CalendarHandler(BaseHandler):
    """
    Handler for iCalendar
    """
    def get(self):
        """
        Render the iCalendar
        """
        if sickbeard.CALENDAR_UNPROTECTED:
            self.write(self.calendar())
        else:
            self.calendar_auth()

    @authenticated
    def calendar_auth(self):
        """
        Render the iCalendar with authentication
        """
        self.write(self.calendar())

    # Raw iCalendar implementation by Pedro Jose Pereira Vieito (@pvieito).
    def calendar(self):
        """
        Provides a subscribable URL for iCal subscriptions
        """
        logger.log('Receiving iCal request from {ip}'.format(ip=self.request.remote_ip))

        # Create a iCal string
        ical = 'BEGIN:VCALENDAR\r\n'
        ical += 'VERSION:2.0\r\n'
        ical += 'X-WR-CALNAME:Medusa\r\n'
        ical += 'X-WR-CALDESC:Medusa\r\n'
        ical += 'PRODID://Medusa Upcoming Episodes//\r\n'

        future_weeks = try_int(self.get_argument('future', 52), 52)
        past_weeks = try_int(self.get_argument('past', 52), 52)

        # Limit dates
        past_date = (datetime.date.today() + datetime.timedelta(weeks=-past_weeks)).toordinal()
        future_date = (datetime.date.today() + datetime.timedelta(weeks=future_weeks)).toordinal()

        # Get all the shows that are not paused and are currently on air (from kjoconnor Fork)
        main_db_con = db.DBConnection()
        calendar_shows = main_db_con.select(
            b'SELECT show_name, indexer_id, network, airs, runtime '
            b'FROM tv_shows '
            b'WHERE ( status = ? OR status = ? ) AND paused != 1',
            ('Continuing', 'Returning Series')
        )
        for show in calendar_shows:
            # Get all episodes of this show airing between today and next month
            episode_list = main_db_con.select(
                b'SELECT indexerid, name, season, episode, description, airdate '
                b'FROM tv_episodes '
                b'WHERE airdate >= ? AND airdate < ? AND showid = ?',
                (past_date, future_date, int(show[b'indexer_id']))
            )

            utc = tz.gettz('GMT')

            for episode in episode_list:

                air_date_time = network_timezones.parse_date_time(episode[b'airdate'], show[b'airs'],
                                                                  show[b'network']).astimezone(utc)
                air_date_time_end = air_date_time + datetime.timedelta(
                    minutes=try_int(show[b'runtime'], 60))

                # Create event for episode
                ical += 'BEGIN:VEVENT\r\n'
                ical += 'DTSTART:{date}\r\n'.format(date=air_date_time.strftime('%Y%m%dT%H%M%SZ'))
                ical += 'DTEND:{date}\r\n'.format(date=air_date_time_end.strftime('%Y%m%dT%H%M%SZ'))
                if sickbeard.CALENDAR_ICONS:
                    icon_url = 'https://cdn.pymedusa.com/images/ico/favicon-16.png'
                    ical += 'X-GOOGLE-CALENDAR-CONTENT-ICON:{icon_url}\r\n'.format(icon_url=icon_url)
                    ical += 'X-GOOGLE-CALENDAR-CONTENT-DISPLAY:CHIP\r\n'
                ical += 'SUMMARY: {show} - {season}x{episode} - {title}\r\n'.format(
                    show=show[b'show_name'],
                    season=episode[b'season'],
                    episode=episode[b'episode'],
                    title=episode[b'name'],
                )
                ical += 'UID:Medusa-{date}-{show}-E{episode}S{season}\r\n'.format(
                    date=datetime.date.today().isoformat(),
                    show=show[b'show_name'].replace(' ', '-'),
                    episode=episode[b'episode'],
                    season=episode[b'season'],
                )
                ical += 'DESCRIPTION: {date} on {network}'.format(
                    date=show[b'airs'] or '(Unknown airs)',
                    network=show[b'network'] or 'Unknown network',
                )
                if episode[b'description']:
                    ical += ' \\n\\n {description}\r\n'.format(description=episode[b'description'].splitlines()[0])
                else:
                    ical += '\r\n'
                ical += 'END:VEVENT\r\n'

        # Ending the iCal
        ical += 'END:VCALENDAR'

        return ical
