# coding=utf-8

# Authors:
# Derek Battams <derek@battams.ca>
# Pedro Jose Pereira Vieito (@pvieito) <pvieito@gmail.com>
#
# URL: https://github.com/pymedusa/SickRage
#
# This file is part of medusa.
#
# medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with medusa. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from __future__ import unicode_literals
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
        msg = MIMEText('This is a test message from Medusa. If you\'re reading this, the test succeeded.')
        if sickbeard.EMAIL_SUBJECT:
            msg[b'Subject'] = '[TEST] ' + sickbeard.EMAIL_SUBJECT
        else:
            msg[b'Subject'] = 'Medusa: Test Message'
        msg[b'From'] = smtp_from
        msg[b'To'] = to
        msg[b'Date'] = formatdate(localtime=True)
        return self._sendmail(host, port, smtp_from, use_tls, user, pwd, [to], msg, True)

    def notify_snatch(self, ep_name, title='Snatched:'):  # pylint: disable=unused-argument
        """
        Send a notification that an episode was snatched

        ep_name: The name of the episode that was snatched
        title: The title of the notification (optional)
        """
        ep_name = ss(ep_name)

        if sickbeard.USE_EMAIL and sickbeard.EMAIL_NOTIFY_ONSNATCH:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if not to:
                logger.log('Skipping email notify because there are no configured recipients', logger.DEBUG)
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Snatched</h3><br>'
                        '<p>Show: <b>{}</b></p><br><p>Episode: <b>{}</b></p><br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format
                        (show, re.search('.+ - (.+?-.+) -.+', ep_name).group(1)),
                        'html'))

                except Exception:
                    try:
                        msg = MIMEText(ep_name)
                    except Exception:
                        msg = MIMEText('Episode Snatched')

                if sickbeard.EMAIL_SUBJECT:
                    msg[b'Subject'] = '[SN] ' + sickbeard.EMAIL_SUBJECT
                else:
                    msg[b'Subject'] = 'Snatched: ' + ep_name
                msg[b'From'] = sickbeard.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                msg[b'Date'] = formatdate(localtime=True)
                if self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS,
                                  sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg):
                    logger.log('Snatch notification sent to [{}] for "{}"'.format(to, ep_name), logger.DEBUG)
                else:
                    logger.log('Snatch notification error: {}'.format(self.last_err), logger.WARNING)

    def notify_download(self, ep_name, title='Completed:'):  # pylint: disable=unused-argument
        """
        Send a notification that an episode was downloaded

        ep_name: The name of the episode that was downloaded
        title: The title of the notification (optional)
        """
        ep_name = ss(ep_name)

        if sickbeard.USE_EMAIL and sickbeard.EMAIL_NOTIFY_ONDOWNLOAD:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if not to:
                logger.log('Skipping email notify because there are no configured recipients', logger.DEBUG)
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Downloaded</h3><br>'
                        '<p>Show: <b>{}</b></p><br><p>Episode: <b>{}</b></p><br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format
                        (show, re.search('.+ - (.+?-.+) -.+', ep_name).group(1)),
                        'html'))

                except Exception:
                    try:
                        msg = MIMEText(ep_name)
                    except Exception:
                        msg = MIMEText('Episode Downloaded')

                if sickbeard.EMAIL_SUBJECT:
                    msg[b'Subject'] = '[DL] ' + sickbeard.EMAIL_SUBJECT
                else:
                    msg[b'Subject'] = 'Downloaded: ' + ep_name
                msg[b'From'] = sickbeard.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                msg[b'Date'] = formatdate(localtime=True)
                if self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS,
                                  sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg):
                    logger.log('Download notification sent to [{}] for "{}"'.format(to, ep_name), logger.DEBUG)
                else:
                    logger.log('Download notification error: {}'.format(self.last_err), logger.WARNING)

    def notify_subtitle_download(self, ep_name, lang, title='Downloaded subtitle:'):  # pylint: disable=unused-argument
        """
        Send a notification that an subtitle was downloaded

        ep_name: The name of the episode that was downloaded
        lang: Subtitle language wanted
        """
        ep_name = ss(ep_name)

        if sickbeard.USE_EMAIL and sickbeard.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if not to:
                logger.log('Skipping email notify because there are no configured recipients', logger.DEBUG)
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Subtitle Downloaded</h3><br>'
                        '<p>Show: <b>{}</b></p><br><p>Episode: <b>{}</b></p><br>'
                        '<p>Language: <b>{}</b></p><br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format
                        (show, re.search('.+ - (.+?-.+) -.+', ep_name).group(1), lang),
                        'html'))
                except Exception:
                    try:
                        msg = MIMEText(ep_name + ': ' + lang)
                    except Exception:
                        msg = MIMEText('Episode Subtitle Downloaded')

                if sickbeard.EMAIL_SUBJECT:
                    msg[b'Subject'] = '[ST] ' + sickbeard.EMAIL_SUBJECT
                else:
                    msg[b'Subject'] = lang + ' Subtitle Downloaded: ' + ep_name
                msg[b'From'] = sickbeard.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                if self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS,
                                  sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg):
                    logger.log('Download notification sent to [{}] for "{}"'.format(to, ep_name), logger.DEBUG)
                else:
                    logger.log('Download notification error: {}'.format(self.last_err), logger.WARNING)

    def notify_git_update(self, new_version='??'):
        """
        Send a notification that Medusa was updated
        new_version: The commit Medusa was updated to
        """
        if sickbeard.USE_EMAIL:
            to = self._generate_recipients(None)
            if not to:
                logger.log('Skipping email notify because there are no configured recipients', logger.DEBUG)
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Updated</h3><br>'
                        '<p>Commit: <b>{}</b></p><br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format
                        (new_version), 'html'))

                except Exception:
                    try:
                        msg = MIMEText(new_version)
                    except Exception:
                        msg = MIMEText('Medusa updated')

                msg[b'Subject'] = 'Updated: {}'.format(new_version)
                msg[b'From'] = sickbeard.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                msg[b'Date'] = formatdate(localtime=True)
                if self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS,
                                  sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg):
                    logger.log('Update notification sent to [{}]'.format(to), logger.DEBUG)
                else:
                    logger.log('Update notification error: {}'.format(self.last_err), logger.WARNING)

    def notify_login(self, ipaddress=''):
        """
        Send a notification that Medusa was logged into remotely
        ipaddress: The ip Medusa was logged into from
        """
        if sickbeard.USE_EMAIL:
            to = self._generate_recipients(None)
            if not to:
                logger.log('Skipping email notify because there are no configured recipients', logger.DEBUG)
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Remote Login</h3><br>'
                        '<p>New login from IP: <a href="http://geomaplookup.net/?ip={0}">{0}</a>.<br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format
                        (ipaddress), 'html'))

                except Exception:
                    try:
                        msg = MIMEText(ipaddress)
                    except Exception:
                        msg = MIMEText('Medusa Remote Login')

                msg[b'Subject'] = 'New Login from IP: {}'.format(ipaddress)
                msg[b'From'] = sickbeard.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                msg[b'Date'] = formatdate(localtime=True)
                if self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS,
                                  sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg):
                    logger.log('Login notification sent to [{}]'.format(to), logger.DEBUG)
                else:
                    logger.log('Login notification error: {}'.format(self.last_err), logger.WARNING)

    @staticmethod
    def _generate_recipients(show):  # pylint: disable=too-many-branches
        addrs = []
        main_db_con = db.DBConnection()

        # Grab the global recipients
        if sickbeard.EMAIL_LIST:
            for addr in sickbeard.EMAIL_LIST.split(','):
                if addr.strip():
                    addrs.append(addr)

        # Grab the per-show-notification recipients
        if show is not None:
            for s in show:
                for subs in main_db_con.select('SELECT notify_list FROM tv_shows WHERE show_name = ?', (s,)):
                    if subs[b'notify_list']:
                        if subs[b'notify_list'][0] == '{':
                            entries = dict(ast.literal_eval(subs[b'notify_list']))
                            for addr in entries[b'emails'].split(','):
                                if addr.strip():
                                    addrs.append(addr)
                        else:                                           # Legacy
                            for addr in subs[b'notify_list'].split(','):
                                if addr.strip():
                                    addrs.append(addr)

        addrs = set(addrs)
        logger.log('Notification recipients: {}'.format(addrs), logger.DEBUG)
        return addrs

    def _sendmail(self, host, port, smtp_from, use_tls, user, pwd, to, msg, smtpDebug=False):  # pylint: disable=too-many-arguments
        logger.log('HOST: {}; PORT: {}; FROM: {}, TLS: {}, USER: {}, PWD: {}, TO: {}'.format(
            host, port, smtp_from, use_tls, user, pwd, to), logger.DEBUG)
        try:
            srv = smtplib.SMTP(host, int(port))
        except Exception as e:
            logger.log('Exception generated while sending e-mail: ' + str(e), logger.WARNING)
            # logger.log(traceback.format_exc(), logger.DEBUG)
            self.last_err = '{}'.format(e)
            return False

        if smtpDebug:
            srv.set_debuglevel(1)
        try:
            if use_tls in ('1', True) or (user and pwd):
                logger.log('Sending initial EHLO command!', logger.DEBUG)
                srv.ehlo()
            if use_tls in ('1', True):
                logger.log('Sending STARTTLS command!', logger.DEBUG)
                srv.starttls()
                srv.ehlo()
            if user and pwd:
                logger.log('Sending LOGIN command!', logger.DEBUG)
                srv.login(user, pwd)

            srv.sendmail(smtp_from, to, msg.as_string())
            srv.quit()
            return True
        except Exception as e:
            self.last_err = '{}'.format(e)
            return False

    @staticmethod
    def _parseEp(ep_name):
        ep_name = ss(ep_name)

        sep = ' - '
        titles = ep_name.split(sep)
        titles.sort(key=len, reverse=True)
        logger.log('TITLES: {}'.format(titles), logger.DEBUG)
        return titles
