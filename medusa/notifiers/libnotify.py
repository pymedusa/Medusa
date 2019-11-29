# coding=utf-8

from __future__ import unicode_literals

import cgi
import logging
import os
from builtins import object

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def diagnose():
    """
    Check the environment for reasons libnotify isn't working.  Return a
    user-readable message indicating possible issues.
    """
    try:
        from gi.repository import Notify  # @UnusedImport
    except ImportError:
        return (u"<p>Error: gir-notify isn't installed. On Ubuntu/Debian, install the "
                u'<a href="apt:gir1.2-notify-0.7">gir1.2-notify-0.7</a> or '
                u'<a href="apt:gir1.0-notify-0.4">gir1.0-notify-0.4</a> package.')
    if 'DISPLAY' not in os.environ and 'DBUS_SESSION_BUS_ADDRESS' not in os.environ:
        return (u'<p>Error: Environment variables DISPLAY and DBUS_SESSION_BUS_ADDRESS '
                u"aren't set.  libnotify will only work when you run Medusa "
                u'from a desktop login.')
    try:
        import dbus
    except ImportError:
        pass
    else:
        try:
            bus = dbus.SessionBus()
        except dbus.DBusException as e:
            return (u'<p>Error: unable to connect to D-Bus session bus: <code>%s</code>.'
                    u'<p>Are you running Medusa in a desktop session?') % (cgi.escape(e),)
        try:
            bus.get_object('org.freedesktop.Notifications',
                           '/org/freedesktop/Notifications')
        except dbus.DBusException as e:
            return (u"<p>Error: there doesn't seem to be a notification daemon available: <code>%s</code> "
                    u'<p>Try installing notification-daemon or notify-osd.') % (cgi.escape(e),)
    return u'<p>Error: Unable to send notification.'


class Notifier(object):
    def __init__(self):
        self.Notify = None
        self.gobject = None

    def init_notify(self):
        if self.Notify is not None:
            return True
        try:
            from gi.repository import Notify
        except ImportError:
            log.warning(u"Unable to import Notify from gi.repository. libnotify notifications won't work.")
            return False
        try:
            from gi.repository import GObject
        except ImportError:
            log.warning(u"Unable to import GObject from gi.repository. We can't catch a GError in display.")
            return False
        if not Notify.init('Medusa'):
            log.warning(u"Initialization of Notify failed. libnotify notifications won't work.")
            return False
        self.Notify = Notify
        self.gobject = GObject
        return True

    def notify_snatch(self, title, message):
        if app.LIBNOTIFY_NOTIFY_ONSNATCH:
            self._notify(title, message)

    def notify_download(self, ep_obj):
        if app.LIBNOTIFY_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_obj.pretty_name_with_quality())

    def notify_subtitle_download(self, ep_obj, lang):
        if app.LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD], ep_obj.pretty_name() + ': ' + lang)

    def notify_git_update(self, new_version='??'):
        if app.USE_LIBNOTIFY:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._notify(title, update_text + new_version)

    def notify_login(self, ipaddress=''):
        if app.USE_LIBNOTIFY:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._notify(title, update_text.format(ipaddress))

    def test_notify(self):
        return self._notify('Test notification', 'This is a test notification from Medusa', force=True)

    def _notify(self, title, message, force=False):
        if not app.USE_LIBNOTIFY and not force:
            return False
        if not self.init_notify():
            return False

        # Can't make this a global constant because PROG_DIR isn't available
        # when the module is imported.
        icon_path = os.path.join(app.THEME_DATA_ROOT, 'assets/img/ico/favicon-120.png')

        # If the session bus can't be acquired here a bunch of warning messages
        # will be printed but the call to show() will still return True.
        # pynotify doesn't seem too keen on error handling.
        n = self.Notify.Notification.new(title, message, icon_path)
        try:
            return n.show()
        except self.gobject.GError:
            return False
