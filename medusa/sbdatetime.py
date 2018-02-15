import datetime
import functools
import locale

from medusa import app
from medusa.network_timezones import app_timezone

date_presets = (
    '%Y-%m-%d',
    '%a, %Y-%m-%d',
    '%A, %Y-%m-%d',
    '%y-%m-%d',
    '%a, %y-%m-%d',
    '%A, %y-%m-%d',
    '%m/%d/%Y',
    '%a, %m/%d/%Y',
    '%A, %m/%d/%Y',
    '%m/%d/%y',
    '%a, %m/%d/%y',
    '%A, %m/%d/%y',
    '%m-%d-%Y',
    '%a, %m-%d-%Y',
    '%A, %m-%d-%Y',
    '%m-%d-%y',
    '%a, %m-%d-%y',
    '%A, %m-%d-%y',
    '%m.%d.%Y',
    '%a, %m.%d.%Y',
    '%A, %m.%d.%Y',
    '%m.%d.%y',
    '%a, %m.%d.%y',
    '%A, %m.%d.%y',
    '%d-%m-%Y',
    '%a, %d-%m-%Y',
    '%A, %d-%m-%Y',
    '%d-%m-%y',
    '%a, %d-%m-%y',
    '%A, %d-%m-%y',
    '%d/%m/%Y',
    '%a, %d/%m/%Y',
    '%A, %d/%m/%Y',
    '%d/%m/%y',
    '%a, %d/%m/%y',
    '%A, %d/%m/%y',
    '%d.%m.%Y',
    '%a, %d.%m.%Y',
    '%A, %d.%m.%Y',
    '%d.%m.%y',
    '%a, %d.%m.%y',
    '%A, %d.%m.%y',
    '%d. %b %Y',
    '%a, %d. %b %Y',
    '%A, %d. %b %Y',
    '%d. %b %y',
    '%a, %d. %b %y',
    '%A, %d. %b %y',
    '%d. %B %Y',
    '%a, %d. %B %Y',
    '%A, %d. %B %Y',
    '%d. %B %y',
    '%a, %d. %B %y',
    '%A, %d. %B %y',
    '%b %d, %Y',
    '%a, %b %d, %Y',
    '%A, %b %d, %Y',
    '%B %d, %Y',
    '%a, %B %d, %Y',
    '%A, %B %d, %Y'
)

time_presets = ('%I:%M:%S %p', '%H:%M:%S')


# helper class
class StaticOrInstance(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return functools.partial(self.func, instance)


# subclass datetime.datetime to add function to display custom date and time formats
class DateTime(datetime.datetime):
    has_locale = True
    en_US_norm = locale.normalize('en_US.utf-8')

    @StaticOrInstance
    def convert_to_setting(self, dt=None):
        try:
            if app.TIMEZONE_DISPLAY == 'local':
                return dt.astimezone(app_timezone) if self is None else self.astimezone(app_timezone)
            else:
                return dt if self is None else self
        except Exception:
            return dt if self is None else self

    # display Time in application Format
    @StaticOrInstance
    def display_time(self, dt=None, show_seconds=False, t_preset=None):
        """
        Display time in application format
        TODO: Rename this to srftime

        :param dt: datetime object
        :param show_seconds: Boolean, show seconds
        :param t_preset: Preset time format
        :return: time string
        """

        try:
            locale.setlocale(locale.LC_TIME, '')
        except Exception:
            pass

        try:
            if DateTime.has_locale:
                locale.setlocale(locale.LC_TIME, 'en_US')
        except Exception:
            try:
                if DateTime.has_locale:
                    locale.setlocale(locale.LC_TIME, DateTime.en_US_norm)
            except Exception:
                DateTime.has_locale = False

        result = ''
        try:
            if self is None:
                if dt is not None:
                    if t_preset is not None:
                        result = dt.strftime(t_preset)
                    elif show_seconds:
                        result = dt.strftime(app.TIME_PRESET_W_SECONDS)
                    else:
                        result = dt.strftime(app.TIME_PRESET)
            else:
                if t_preset is not None:
                    result = self.strftime(t_preset)
                elif show_seconds:
                    result = self.strftime(app.TIME_PRESET_W_SECONDS)
                else:
                    result = self.strftime(app.TIME_PRESET)
        finally:
            try:
                if DateTime.has_locale:
                    locale.setlocale(locale.LC_TIME, '')
            except Exception:
                DateTime.has_locale = False

        return result.decode(app.SYS_ENCODING)

    # display Date in application Format
    @StaticOrInstance
    def display_date(self, dt=None, d_preset=None):
        """
        Display date in application format
        TODO: Rename this to srfdate

        :param dt: datetime object
        :param d_preset: Preset date format
        :return: date string
        """

        try:
            locale.setlocale(locale.LC_TIME, '')
        except Exception:
            pass

        result = ''
        try:
            if self is None:
                if dt is not None:
                    if d_preset is not None:
                        result = dt.strftime(d_preset)
                    else:
                        result = dt.strftime(app.DATE_PRESET)
            else:
                if d_preset is not None:
                    result = self.strftime(d_preset)
                else:
                    result = self.strftime(app.DATE_PRESET)
        finally:

            try:
                locale.setlocale(locale.LC_TIME, '')
            except Exception:
                pass

        return result.decode(app.SYS_ENCODING)

    # display Datetime in application Format
    @StaticOrInstance
    def display_datetime(self, dt=None, show_seconds=False, d_preset=None, t_preset=None):
        """
        Show datetime in application format
        TODO: Rename this to srfdatetime

        :param dt: datetime object
        :param show_seconds: Boolean, show seconds as well
        :param d_preset: Preset date format
        :param t_preset: Preset time format
        :return: datetime string
        """

        try:
            locale.setlocale(locale.LC_TIME, '')
        except Exception:
            pass

        result = ''
        try:
            if self is None:
                if dt is not None:
                    if d_preset is not None:
                        result = dt.strftime(d_preset)
                    else:
                        result = dt.strftime(app.DATE_PRESET)
                    try:
                        if DateTime.has_locale:
                            locale.setlocale(locale.LC_TIME, 'en_US')
                    except Exception:
                        try:
                            if DateTime.has_locale:
                                locale.setlocale(locale.LC_TIME, DateTime.en_US_norm)
                        except Exception:
                            DateTime.has_locale = False
                    if t_preset is not None:
                        result += ', ' + dt.strftime(t_preset)
                    elif show_seconds:
                        result += ', ' + dt.strftime(app.TIME_PRESET_W_SECONDS)
                    else:
                        result += ', ' + dt.strftime(app.TIME_PRESET)
            else:
                if d_preset is not None:
                    result = self.strftime(d_preset)
                else:
                    result = self.strftime(app.DATE_PRESET)
                try:
                    if DateTime.has_locale:
                        locale.setlocale(locale.LC_TIME, 'en_US')
                except Exception:
                    try:
                        if DateTime.has_locale:
                            locale.setlocale(locale.LC_TIME, DateTime.en_US_norm)
                    except Exception:
                        DateTime.has_locale = False
                if t_preset is not None:
                    result += ', ' + self.strftime(t_preset)
                elif show_seconds:
                    result += ', ' + self.strftime(app.TIME_PRESET_W_SECONDS)
                else:
                    result += ', ' + self.strftime(app.TIME_PRESET)
        finally:
            try:
                if DateTime.has_locale:
                    locale.setlocale(locale.LC_TIME, '')
            except Exception:
                DateTime.has_locale = False

        return result.decode(app.SYS_ENCODING)
