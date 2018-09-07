# coding=utf-8
"""Email notifier module."""

from __future__ import unicode_literals

import ast
import logging
import re
import smtplib
from builtins import object
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from medusa import app, db
from medusa.helper.encoding import ss
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """
    Email notifier class.

    Possible patterns for the `ep_name` input:
        Downloaded/Snatched:
            %SN - %Sx%0E - %EN - %QN
            %SN - %Sx%0E - %AB - %EN - %QN
        Subtitle Downloaded:
            %SN - %AB - %EN
            %SN - %AD - %EN
            %SN - S%0SE%0E - %EN
    """

    name_pattern = re.compile(
        r'(?P<show>.+?) - '
        r'(?P<ep_id>S?\d+[Ex]\d+( - \d{3})?|\d{3}|\d{4}-\d{2}-\d{2}) - '
        r'(?P<episode>.*)'
    )

    def __init__(self):
        self.last_err = None

    def test_notify(self, host, port, smtp_from, use_tls, user, pwd, to):
        """
        Send a test notification.

        :return: True for no issue or False if there was an error
        """
        msg = MIMEText('This is a test message from Medusa. If you\'re reading this, the test succeeded.')
        if app.EMAIL_SUBJECT:
            msg['Subject'] = '[TEST] ' + app.EMAIL_SUBJECT
        else:
            msg['Subject'] = 'Medusa: Test Message'
        msg['From'] = smtp_from
        msg['To'] = to
        msg['Date'] = formatdate(localtime=True)
        return self._sendmail(host, port, smtp_from, use_tls, user, pwd, [to], msg, True)

    def notify_snatch(self, ep_name, is_proper, title='Snatched:'):
        """
        Send a notification that an episode was snatched.

        ep_name: The name of the episode that was snatched
        title: The title of the notification (optional)
        """
        ep_name = ss(ep_name)

        if app.USE_EMAIL and app.EMAIL_NOTIFY_ONSNATCH:
            parsed = self._parse_name(ep_name)
            to = self._generate_recipients(parsed['show'])
            if not to:
                log.debug('Skipping email notify because there are no configured recipients')
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Snatched</h3><br>'
                        '<p>Show: <b>{show}</b></p><br>'
                        '<p>Episode: <b>{ep_id}{episode}</b></p><br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format(
                            show=parsed['show'],
                            ep_id=(parsed['ep_id'] + ' - ') if 'ep_id' in parsed else '',
                            episode=parsed['episode']
                        ),
                        'html'))

                except Exception:
                    try:
                        msg = MIMEText(ep_name)
                    except Exception:
                        msg = MIMEText('Episode Snatched')

                if app.EMAIL_SUBJECT:
                    msg['Subject'] = '[SN] ' + app.EMAIL_SUBJECT
                else:
                    msg['Subject'] = 'Snatched: ' + ep_name
                msg['From'] = app.EMAIL_FROM
                msg['To'] = ','.join(to)
                msg['Date'] = formatdate(localtime=True)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Snatch notification sent to {recipient} for {episode}',
                              {'recipient': to, 'episode': ep_name})
                else:
                    log.warning('Snatch notification error: {0}', self.last_err)

    def notify_download(self, ep_name, title='Completed:'):
        """
        Send a notification that an episode was downloaded.

        ep_name: The name of the episode that was downloaded
        title: The title of the notification (optional)
        """
        ep_name = ss(ep_name)

        if app.USE_EMAIL and app.EMAIL_NOTIFY_ONDOWNLOAD:
            parsed = self._parse_name(ep_name)
            to = self._generate_recipients(parsed['show'])
            if not to:
                log.debug('Skipping email notify because there are no configured recipients')
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Downloaded</h3><br>'
                        '<p>Show: <b>{show}</b></p><br>'
                        '<p>Episode: <b>{ep_id}{episode}</b></p><br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format(
                            show=parsed['show'],
                            ep_id=(parsed['ep_id'] + ' - ') if 'ep_id' in parsed else '',
                            episode=parsed['episode']
                        ),
                        'html'))

                except Exception:
                    try:
                        msg = MIMEText(ep_name)
                    except Exception:
                        msg = MIMEText('Episode Downloaded')

                if app.EMAIL_SUBJECT:
                    msg['Subject'] = '[DL] ' + app.EMAIL_SUBJECT
                else:
                    msg['Subject'] = 'Downloaded: ' + ep_name
                msg['From'] = app.EMAIL_FROM
                msg['To'] = ','.join(to)
                msg['Date'] = formatdate(localtime=True)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Download notification sent to {recipient} for {episode}',
                              {'recipient': to, 'episode': ep_name})
                else:
                    log.warning('Download notification error: {0}', self.last_err)

    def notify_subtitle_download(self, ep_name, lang, title='Downloaded subtitle:'):
        """
        Send a notification that a subtitle was downloaded.

        ep_name: The name of the episode that was downloaded
        lang: Subtitle language wanted
        """
        ep_name = ss(ep_name)

        if app.USE_EMAIL and app.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD:
            parsed = self._parse_name(ep_name)
            to = self._generate_recipients(parsed['show'])
            if not to:
                log.debug('Skipping email notify because there are no configured recipients')
            else:
                try:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(
                        '<body style="font-family:Helvetica, Arial, sans-serif;">'
                        '<h3>Medusa Notification - Subtitle Downloaded</h3><br>'
                        '<p>Show: <b>{show}</b></p><br>'
                        '<p>Episode: <b>{ep_id}{episode}</b></p><br>'
                        '<p>Language: <b>{lang}</b></p><br><br>'
                        '<footer style="margin-top: 2.5em; padding: .7em 0; '
                        'color: #777; border-top: #BBB solid 1px;">'
                        'Powered by Medusa.</footer></body>'.format(
                            show=parsed['show'],
                            ep_id=(parsed['ep_id'] + ' - ') if 'ep_id' in parsed else '',
                            episode=parsed['episode'],
                            lang=lang
                        ),
                        'html'))
                except Exception:
                    try:
                        msg = MIMEText(ep_name + ': ' + lang)
                    except Exception:
                        msg = MIMEText('Episode Subtitle Downloaded')

                if app.EMAIL_SUBJECT:
                    msg['Subject'] = '[ST] ' + app.EMAIL_SUBJECT
                else:
                    msg['Subject'] = lang + ' Subtitle Downloaded: ' + ep_name
                msg['From'] = app.EMAIL_FROM
                msg['To'] = ','.join(to)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Download notification sent to {recipient} for {episode}',
                              {'recipient': to, 'episode': ep_name})
                else:
                    log.warning('Download notification error: {0}', self.last_err)

    def notify_git_update(self, new_version='??'):
        """
        Send a notification that Medusa was updated.

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

                msg['Subject'] = 'Updated: {0}'.format(new_version)
                msg['From'] = app.EMAIL_FROM
                msg['To'] = ','.join(to)
                msg['Date'] = formatdate(localtime=True)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Update notification sent to {recipient}',
                              {'recipient': to})
                else:
                    log.warning('Update notification error: {0}', self.last_err)

    def notify_login(self, ipaddress=''):
        """
        Send a notification that Medusa was logged into remotely.

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

                msg['Subject'] = 'New Login from IP: {0}'.format(ipaddress)
                msg['From'] = app.EMAIL_FROM
                msg['To'] = ','.join(to)
                msg['Date'] = formatdate(localtime=True)
                if self._sendmail(app.EMAIL_HOST, app.EMAIL_PORT, app.EMAIL_FROM, app.EMAIL_TLS,
                                  app.EMAIL_USER, app.EMAIL_PASSWORD, to, msg):
                    log.debug('Login notification sent to {recipient}', {'recipient': to})
                else:
                    log.warning('Login notification error: {0}', self.last_err)

    @staticmethod
    def _generate_recipients(show):
        addrs = []
        main_db_con = db.DBConnection()

        # Grab the global recipients
        if app.EMAIL_LIST:
            addrs.extend(
                addr for addr in app.EMAIL_LIST
                if addr.strip()
            )

        # Grab the per-show-notification recipients
        if show:
            sql_results = main_db_con.select(
                'SELECT notify_list '
                'FROM tv_shows '
                'WHERE show_name = ?',
                [show]
            )
            for row in sql_results:
                notify_list = row['notify_list']
                if not notify_list:
                    continue

                if notify_list[0] == '{':
                    entries = dict(ast.literal_eval(notify_list))
                    notify_list = entries['emails']

                addrs.extend(
                    addr for addr in notify_list.split(',')
                    if addr.strip()
                )

        addrs = set(addrs)
        log.debug('Notification recipients: {0}', addrs)
        return addrs

    def _sendmail(self, host, port, smtp_from, use_tls, user, pwd, to, msg, smtp_debug=False):
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

        if smtp_debug:
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

    @classmethod
    def _parse_name(cls, ep_name):
        ep_name = ss(ep_name)

        # @TODO: Prone to issues, best solution is to have a dictionary passed to notifiers
        match = cls.name_pattern.match(ep_name)

        # Fallback
        if not match:
            # @TODO: This won't be needed when notifiers receive a dictionary
            log.warning('Unable to parse "{0}" for email notification', ep_name)
            titles = ep_name.split(' - ')
            return {
                'show': titles[0],
                'episode': ' - '.join(titles[1:])
            }

        result = match.groupdict()

        log.debug('Email notifier parsed "{0}" into {1!r}',
                  ep_name, result)
        return result
