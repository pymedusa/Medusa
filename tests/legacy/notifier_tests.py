# coding=UTF-8
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
#
################################################################################
# As a test case, there are instances in which it is necessary to call protected members of
# classes in order to test those classes.  Therefore we will be pylint disable protected-access

"""Test notifiers."""

from __future__ import print_function

from medusa import db
from medusa.helper.encoding import ss
from medusa.notifiers.emailnotify import Notifier as EmailNotifier
from medusa.notifiers.prowl import Notifier as ProwlNotifier
from medusa.server.web import Home
from medusa.tv import Episode, Series
from tests.legacy import test_lib as test


class NotifierTests(test.AppTestDBCase):
    """Test notifiers."""

    @classmethod
    def setUpClass(cls):
        """Set up class for tests."""
        num_legacy_shows = 3
        num_shows = 3
        num_episodes_per_show = 5
        cls.mydb = db.DBConnection()
        cls.legacy_shows = []
        cls.shows = []

        # Per-show-notifications were originally added for email notifications only.  To add
        # this feature to other notifiers, it was necessary to alter the way text is stored in
        # one of the DB columns.  Therefore, to test properly, we must create some shows that
        # store emails in the old method (legacy method) and then other shows that will use
        # the new method.
        for show_counter in range(100, 100 + num_legacy_shows):
            show = Series(1, show_counter)
            show.name = "Show " + str(show_counter)
            show.episodes = []
            for episode_counter in range(0, num_episodes_per_show):
                episode = Episode(show, test.SEASON, episode_counter)
                episode.name = "Episode " + str(episode_counter + 1)
                episode.quality = "SDTV"
                show.episodes.append(episode)
            show.save_to_db()
            cls.legacy_shows.append(show)

        for show_counter in range(200, 200 + num_shows):
            show = Series(1, show_counter)
            show.name = "Show " + str(show_counter)
            show.episodes = []
            for episode_counter in range(0, num_episodes_per_show):
                episode = Episode(show, test.SEASON, episode_counter)
                episode.name = "Episode " + str(episode_counter + 1)
                episode.quality = "SDTV"
                show.episodes.append(episode)
            show.save_to_db()
            cls.shows.append(show)

    def setUp(self):
        """Set up tests."""
        self._debug_spew("\n\r")

    def test_email(self):
        """Test email notifications."""
        email_notifier = EmailNotifier()

        # Per-show-email notifications were added early on and utilized a different format than the other notifiers.
        # Therefore, to test properly (and ensure backwards compatibility), this routine will test shows that use
        # both the old and the new storage methodology
        legacy_test_emails = "email-1@address.com,email2@address.org,email_3@address.tv"
        test_emails = "email-4@address.com,email5@address.org,email_6@address.tv"

        for show in self.legacy_shows:
            showid = self._get_showid_by_showname(show.name)
            self.mydb.action("UPDATE tv_shows SET notify_list = ? WHERE show_id = ?", [legacy_test_emails, showid])

        for show in self.shows:
            showid = self._get_showid_by_showname(show.name)
            Home.saveShowNotifyList(indexername='tvdb', seriesid=showid, emails=test_emails)

        # Now, iterate through all shows using the email list generation routines that are used in the notifier proper
        shows = self.legacy_shows + self.shows
        for show in shows:
            for episode in show.episodes:
                ep_name = ss(episode._format_pattern('%SN - %Sx%0E - %EN - ') + episode.quality)  # pylint: disable=protected-access
                show_name = email_notifier._parseEp(ep_name)  # pylint: disable=protected-access
                recipients = email_notifier._generate_recipients(show_name)  # pylint: disable=protected-access
                self._debug_spew("- Email Notifications for " + show.name + " (episode: " + episode.name + ") will be sent to:")
                for email in recipients:
                    self._debug_spew("-- " + email.strip())
                self._debug_spew("\n\r")

        return True

    def test_prowl(self):
        """Test prowl notifications."""
        prowl_notifier = ProwlNotifier()

        # Prowl per-show-notifications only utilize the new methodology for storage; therefore, the list of legacy_shows
        # will not be altered (to preserve backwards compatibility testing)
        test_prowl_apis = "11111111111111111111,22222222222222222222"

        for show in self.shows:
            showid = self._get_showid_by_showname(show.name)
            Home.saveShowNotifyList(indexername='tvdb', seriesid=showid, prowlAPIs=test_prowl_apis)

        # Now, iterate through all shows using the Prowl API generation routines that are used in the notifier proper
        for show in self.shows:
            for episode in show.episodes:
                ep_name = ss(episode._format_pattern('%SN - %Sx%0E - %EN - ') + episode.quality)  # pylint: disable=protected-access
                show_name = prowl_notifier._parse_episode(ep_name)  # pylint: disable=protected-access
                recipients = prowl_notifier._generate_recipients(show_name)  # pylint: disable=protected-access
                self._debug_spew("- Prowl Notifications for " + show.name + " (episode: " + episode.name + ") will be sent to:")
                for api in recipients:
                    self._debug_spew("-- " + api.strip())
                self._debug_spew("\n\r")

        return True

    @staticmethod
    def _debug_spew(text):
        """Spew text notifications.

        :param text: to spew
        :return:
        """
        if __name__ == '__main__' and text is not None:
            print(text)

    def _get_showid_by_showname(self, showname):
        """Get show ID by show name.

        :param showname:
        :return:
        """
        if showname is not None:
            rows = self.mydb.select("SELECT show_id FROM tv_shows WHERE show_name = ?", [showname])
            if len(rows) == 1:
                return rows[0]['show_id']
        return -1
