# coding=utf-8

# Authors:
# Derek Battams <derek@battams.ca>
# Pedro Jose Pereira Vieito (@pvieito) <pvieito@gmail.com>
#
# URL: https://github.com/echel0n/SickRage
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
#
##############################################################################

import smtplib
# import traceback
import ast
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

import re

import sickbeard

from sickbeard import logger
from sickbeard import db
from sickrage.helper.encoding import ss


class Notifier(object):
    def __init__(self):
        self.last_err = None

    def test_notify(self, host, port, smtp_from, use_tls, user, pwd, to):  # pylint: disable=too-many-arguments
        msg = MIMEText('This is a test message from SickRage.  If you\'re reading this, the test succeeded.')
        msg['Subject'] = 'SickRage: Test Message'
        msg['From'] = smtp_from
        msg['To'] = to
        msg['Date'] = formatdate(localtime=True)
        return self._sendmail(host, port, smtp_from, use_tls, user, pwd, [to], msg, True)

    def notify_snatch(self, ep_name, title="Snatched:"):  # pylint: disable=unused-argument
        """
        Send a notification that an episode was snatched

        ep_name: The name of the episode that was snatched
        title: The title of the notification (optional)
        """
        ep_name = ss(ep_name)

        if sickbeard.USE_EMAIL and sickbeard.EMAIL_NOTIFY_ONSNATCH:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if len(to) == 0:
                logger.log(u'Skipping email notify because there are no configured recipients', logger.DEBUG)
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        "<body style='font-family:Helvetica, Arial, sans-serif;'>"
                        "<h3>SickRage Notification - Snatched</h3>\n"
                        "<p>Show: <b>{}</b></p>\n<p>Episode: <b>{}</b></p>\n\n"
                        "<footer style='margin-top: 2.5em; padding: .7em 0; "
                        "color: #777; border-top: #BBB solid 1px;'>"
                        "Powered by SickRage.</footer></body>".format
                        (show, re.search(".+ - (.+?-.+) -.+", ep_name).group(1)),
                        'html'))

                except Exception:
                    try:
                        msg = MIMEText(ep_name)
                    except Exception:
                        msg = MIMEText("Episode Snatched")

                msg['Subject'] = 'Snatched: ' + ep_name
                msg['From'] = sickbeard.EMAIL_FROM
                msg['To'] = ','.join(to)
                msg['Date'] = formatdate(localtime=True)
                if self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS,
                                  sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg):
                    logger.log(u"Snatch notification sent to [{0!s}] for '{1!s}'".format(to, ep_name), logger.DEBUG)
                else:
                    logger.log(u"Snatch notification error: {0!s}".format(self.last_err), logger.WARNING)

    def notify_download(self, ep_name, title="Completed:"):  # pylint: disable=unused-argument
        """
        Send a notification that an episode was downloaded

        ep_name: The name of the episode that was downloaded
        title: The title of the notification (optional)
        """
        ep_name = ss(ep_name)

        if sickbeard.USE_EMAIL and sickbeard.EMAIL_NOTIFY_ONDOWNLOAD:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if len(to) == 0:
                logger.log(u'Skipping email notify because there are no configured recipients', logger.DEBUG)
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        "<body style='font-family:Helvetica, Arial, sans-serif;'>"
                        "<h3>SickRage Notification - Downloaded</h3>\n"
                        "<p>Show: <b>{}</b></p>\n<p>Episode: <b>{}</b></p>\n\n"
                        "<footer style='margin-top: 2.5em; padding: .7em 0; "
                        "color: #777; border-top: #BBB solid 1px;'>"
                        "Powered by SickRage.</footer></body>".format
                        (show, re.search(".+ - (.+?-.+) -.+", ep_name).group(1)),
                        'html'))

                except Exception:
                    try:
                        msg = MIMEText(ep_name)
                    except Exception:
                        msg = MIMEText('Episode Downloaded')

                msg['Subject'] = 'Downloaded: ' + ep_name
                msg['From'] = sickbeard.EMAIL_FROM
                msg['To'] = ','.join(to)
                msg['Date'] = formatdate(localtime=True)
                if self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS,
                                  sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg):
                    logger.log(u"Download notification sent to [{0!s}] for '{1!s}'".format(to, ep_name), logger.DEBUG)
                else:
                    logger.log(u"Download notification error: {0!s}".format(self.last_err), logger.WARNING)

    def notify_subtitle_download(self, ep_name, lang, title="Downloaded subtitle:"):  # pylint: disable=unused-argument
        """
        Send a notification that an subtitle was downloaded

        ep_name: The name of the episode that was downloaded
        lang: Subtitle language wanted
        """
        ep_name = ss(ep_name)

        if sickbeard.USE_EMAIL and sickbeard.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if len(to) == 0:
                logger.log(u'Skipping email notify because there are no configured recipients', logger.DEBUG)
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        "<body style='font-family:Helvetica, Arial, sans-serif;'>"
                        "<h3>SickRage Notification - Subtitle Downloaded</h3>\n"
                        "<p>Show: <b>{}</b></p>\n<p>Episode: <b>{}</b></p>\n"
                        "<p>Language: <b>{}</b></p>\n\n"
                        "<footer style='margin-top: 2.5em; padding: .7em 0; "
                        "color: #777; border-top: #BBB solid 1px;'>"
                        "Powered by SickRage.</footer></body>".format
                        (show, re.search(".+ - (.+?-.+) -.+", ep_name).group(1), lang),
                        'html'))
                except Exception:
                    try:
                        msg = MIMEText(ep_name + ": " + lang)
                    except Exception:
                        msg = MIMEText("Episode Subtitle Downloaded")

                msg['Subject'] = lang + ' Subtitle Downloaded: ' + ep_name
                msg['From'] = sickbeard.EMAIL_FROM
                msg['To'] = ','.join(to)
                if self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS,
                                  sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg):
                    logger.log(u"Download notification sent to [{0!s}] for '{1!s}'".format(to, ep_name), logger.DEBUG)
                else:
                    logger.log(u"Download notification error: {0!s}".format(self.last_err), logger.WARNING)

    def notify_git_update(self, new_version="??"):
        pass

    def notify_login(self, ipaddress=""):
        pass

    @staticmethod
    def _generate_recipients(show):  # pylint: disable=too-many-branches
        addrs = []
        main_db_con = db.DBConnection()

        # Grab the global recipients
        if sickbeard.EMAIL_LIST:
            for addr in sickbeard.EMAIL_LIST.split(','):
                if len(addr.strip()) > 0:
                    addrs.append(addr)

        # Grab the per-show-notification recipients
        if show is not None:
            for s in show:
                for subs in main_db_con.select("SELECT notify_list FROM tv_shows WHERE show_name = ?", (s,)):
                    if subs['notify_list']:
                        if subs['notify_list'][0] == '{':
                            entries = dict(ast.literal_eval(subs['notify_list']))
                            for addr in entries['emails'].split(','):
                                if len(addr.strip()) > 0:
                                    addrs.append(addr)
                        else:                                           # Legacy
                            for addr in subs['notify_list'].split(','):
                                if len(addr.strip()) > 0:
                                    addrs.append(addr)

        addrs = set(addrs)
        logger.log(u'Notification recipients: {0!s}'.format(addrs), logger.DEBUG)
        return addrs

    def _sendmail(self, host, port, smtp_from, use_tls, user, pwd, to, msg, smtpDebug=False):  # pylint: disable=too-many-arguments
        logger.log(u'HOST: {0!s}; PORT: {1!s}; FROM: {2!s}, TLS: {3!s}, USER: {4!s}, PWD: {5!s}, TO: {6!s}'.format(
            host, port, smtp_from, use_tls, user, pwd, to), logger.DEBUG)
        try:
            srv = smtplib.SMTP(host, int(port))
        except Exception as e:
            logger.log(u"Exception generated while sending e-mail: " + str(e), logger.WARNING)
            # logger.log(traceback.format_exc(), logger.DEBUG)
            self.last_err = '{0!s}'.format(e)
            return False

        if smtpDebug:
            srv.set_debuglevel(1)
        try:
            if use_tls in ('1', True) or (user and pwd):
                logger.log(u'Sending initial EHLO command!', logger.DEBUG)
                srv.ehlo()
            if use_tls in ('1', True):
                logger.log(u'Sending STARTTLS command!', logger.DEBUG)
                srv.starttls()
                srv.ehlo()
            if user and pwd:
                logger.log(u'Sending LOGIN command!', logger.DEBUG)
                srv.login(user, pwd)

            srv.sendmail(smtp_from, to, msg.as_string())
            srv.quit()
            return True
        except Exception as e:
            self.last_err = '{0!s}'.format(e)
            return False

    @staticmethod
    def _parseEp(ep_name):
        ep_name = ss(ep_name)

        sep = " - "
        titles = ep_name.split(sep)
        titles.sort(key=len, reverse=True)
        logger.log(u"TITLES: {0!s}".format(titles), logger.DEBUG)
        return titles
