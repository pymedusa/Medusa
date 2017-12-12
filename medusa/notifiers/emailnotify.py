# coding=utf-8

from __future__ import unicode_literals

import ast
import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from medusa import app, db
from medusa.helper.encoding import ss
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def __init__(self):
        self.last_err = None

    def test_notify(self, host, port, smtp_from, use_tls, user, pwd, to):  # pylint: disable=too-many-arguments
        msg = MIMEText('This is a test message from Medusa. If you\'re reading this, the test succeeded.')
        if app.EMAIL_SUBJECT:
            msg[b'Subject'] = '[TEST] ' + app.EMAIL_SUBJECT
        else:
            msg[b'Subject'] = 'Medusa: Test Message'
        msg[b'From'] = smtp_from
        msg[b'To'] = to
        msg[b'Date'] = formatdate(localtime=True)
        return self._sendmail(host, port, smtp_from, use_tls, user, pwd, [to], msg, True)

    def notify_snatch(self, ep_name, is_proper, title='Snatched:'):  # pylint: disable=unused-argument
        """
        Send a notification that an episode was snatched

        ep_name: The name of the episode that was snatched
        title: The title of the notification (optional)
        """
        ep_name = ss(ep_name)

        if app.USE_EMAIL and app.EMAIL_NOTIFY_ONSNATCH:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if not to:
                log.debug('Skipping email notify because there are no configured recipients')
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Snatched</h3><br>'
                        '<p>Show: <b>{0}</b></p><br><p>Episode: <b>{1}</b></p><br><br>'
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

                if app.EMAIL_SUBJECT:
                    msg[b'Subject'] = '[SN] ' + app.EMAIL_SUBJECT
                else:
                    msg[b'Subject'] = 'Snatched: ' + ep_name
                msg[b'From'] = app.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                msg[b'Date'] = formatdate(localtime=True)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Snatch notification sent to {recipient} for {episode}',
                              {'recipient': to, 'episode': ep_name})
                else:
                    log.warning('Snatch notification error: {0}', self.last_err)

    def notify_download(self, ep_name, title='Completed:'):  # pylint: disable=unused-argument
        """
        Send a notification that an episode was downloaded

        ep_name: The name of the episode that was downloaded
        title: The title of the notification (optional)
        """
        ep_name = ss(ep_name)

        if app.USE_EMAIL and app.EMAIL_NOTIFY_ONDOWNLOAD:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if not to:
                log.debug('Skipping email notify because there are no configured recipients')
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Downloaded</h3><br>'
                        '<p>Show: <b>{0}</b></p><br><p>Episode: <b>{1}</b></p><br><br>'
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

                if app.EMAIL_SUBJECT:
                    msg[b'Subject'] = '[DL] ' + app.EMAIL_SUBJECT
                else:
                    msg[b'Subject'] = 'Downloaded: ' + ep_name
                msg[b'From'] = app.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                msg[b'Date'] = formatdate(localtime=True)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Download notification sent to {recipient} for {episode}',
                              {'recipient': to, 'episode': ep_name})
                else:
                    log.warning('Download notification error: {0}', self.last_err)

    def notify_subtitle_download(self, ep_name, lang, title='Downloaded subtitle:'):  # pylint: disable=unused-argument
        """
        Send a notification that an subtitle was downloaded

        ep_name: The name of the episode that was downloaded
        lang: Subtitle language wanted
        """
        ep_name = ss(ep_name)

        if app.USE_EMAIL and app.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD:
            show = self._parseEp(ep_name)
            to = self._generate_recipients(show)
            if not to:
                log.debug('Skipping email notify because there are no configured recipients')
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Subtitle Downloaded</h3><br>'
                        '<p>Show: <b>{0}</b></p><br><p>Episode: <b>{1}</b></p><br>'
                        '<p>Language: <b>{2}</b></p><br><br>'
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

                if app.EMAIL_SUBJECT:
                    msg[b'Subject'] = '[ST] ' + app.EMAIL_SUBJECT
                else:
                    msg[b'Subject'] = lang + ' Subtitle Downloaded: ' + ep_name
                msg[b'From'] = app.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Download notification sent to {recipient} for {episode}',
                              {'recipient': to, 'episode': ep_name})
                else:
                    log.warning('Download notification error: {0}', self.last_err)

    def notify_git_update(self, new_version='??'):
        """
        Send a notification that Medusa was updated
        new_version: The commit Medusa was updated to
        """
        if app.USE_EMAIL:
            to = self._generate_recipients(None)
            if not to:
                log.debug('Skipping email notify because there are no configured recipients')
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Updated</h3><br>'
                        '<p>Commit: <b>{0}</b></p><br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format
                        (new_version), 'html'))

                except Exception:
                    try:
                        msg = MIMEText(new_version)
                    except Exception:
                        msg = MIMEText('Medusa updated')

                msg[b'Subject'] = 'Updated: {0}'.format(new_version)
                msg[b'From'] = app.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                msg[b'Date'] = formatdate(localtime=True)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Update notification sent to {recipient}',
                              {'recipient': to})
                else:
                    log.warning('Update notification error: {0}', self.last_err)

    def notify_login(self, ipaddress=''):
        """
        Send a notification that Medusa was logged into remotely
        ipaddress: The ip Medusa was logged into from
        """
        if app.USE_EMAIL:
            to = self._generate_recipients(None)
            if not to:
                log.debug('Skipping email notify because there are no configured recipients')
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

                msg[b'Subject'] = 'New Login from IP: {0}'.format(ipaddress)
                msg[b'From'] = app.EMAIL_FROM
                msg[b'To'] = ','.join(to)
                msg[b'Date'] = formatdate(localtime=True)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Login notification sent to {recipient}', {'recipient': to})
                else:
                    log.warning('Login notification error: {0}', self.last_err)

    @staticmethod
    def _generate_recipients(show):  # pylint: disable=too-many-branches
        addrs = []
        main_db_con = db.DBConnection()

        # Grab the global recipients
        if app.EMAIL_LIST:
            for addr in app.EMAIL_LIST:
                if addr.strip():
                    addrs.append(addr)

        # Grab the per-show-notification recipients
        if show is not None:
            for s in show:
                for subs in main_db_con.select(
                        'SELECT notify_list '
                        'FROM tv_shows '
                        'WHERE show_name = ?',
                        (s,)):
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
        log.debug('Notification recipients: {0}', addrs)
        return addrs

    def _sendmail(self, host, port, smtp_from, use_tls, user, pwd, to, msg, smtpDebug=False):  # pylint: disable=too-many-arguments
        log.debug(
            'HOST: {host}; PORT: {port}; FROM: {sender}, TLS: {tls},'
            ' USER: {user}, PWD: {password}, TO: {recipient}', {
                'host': host,
                'port': port,
                'sender': smtp_from,
                'tls': use_tls,
                'user': user,
                'password': pwd,
                'recipient': to,
            }
        )
        try:
            srv = smtplib.SMTP(host, int(port))
        except Exception as error:
            log.warning('Exception generated while sending e-mail: {0}', error)
            # logger.log(traceback.format_exc(), logger.DEBUG)
            self.last_err = '{0}'.format(error)
            return False

        if smtpDebug:
            srv.set_debuglevel(1)
        try:
            if use_tls in ('1', True) or (user and pwd):
                log.debug('Sending initial EHLO command!')
                srv.ehlo()
            if use_tls in ('1', True):
                log.debug('Sending STARTTLS command!')
                srv.starttls()
                srv.ehlo()
            if user and pwd:
                log.debug('Sending LOGIN command!')
                srv.login(user.encode('utf-8'), pwd.encode('utf-8'))

            srv.sendmail(smtp_from, to, msg.as_string())
            srv.quit()
            return True
        except Exception as error:
            self.last_err = '{0}'.format(error)
            return False

    @staticmethod
    def _parseEp(ep_name):
        ep_name = ss(ep_name)

        sep = ' - '
        titles = ep_name.split(sep)
        titles.sort(key=len, reverse=True)
        log.debug('TITLES: {0}', titles)
        return titles
