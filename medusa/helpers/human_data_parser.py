from datetime import datetime
from parsedatetime import Calendar
from pytz import timezone
from medusa.logger.adapters.style import BraceAdapter
import logging
from dateutil import parser, tz


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class MedusaDateParser(Calendar):
    """Parsedatetime parser."""
    def __init__(self, *args, **kwargs):
        super(MedusaDateParser, self).__init__(*args, **kwargs)
        self.now_alias = ['just now', 'right now']

    def parse_past(self, pubdate, provided_timezone, human=False):
        if not pubdate:
            log.info('You need to pass a date string as a formatted date or human readable date, like 3 days ago.')
            return None

        if pubdate in self.now_alias:
            pubdate = 'now'

        try:
            if human:
                if not provided_timezone:
                    dt_struct, parse_status = super(MedusaDateParser, self).parse(pubdate)
                    dt = datetime(*dt_struct[:6])
                else:
                    # If a timzone is provided like Europe/Paris, pass it to parseDT
                    dt, parse_status = super(MedusaDateParser, self).parseDT(
                        datetimeString=pubdate, tzinfo=timezone(provided_timezone)
                    )
            else:
                dt = parser.parse(pubdate, fuzzy=True)
                parse_status = 3

            if not parse_status:
                log.info('This is not a valid date format: {pubdate]. Leaving it empty.', {'pubdate': pubdate})
                return None

            # Always make UTC aware if naive
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                dt = dt.replace(tzinfo=tz.tzlocal())
            if provided_timezone:
                dt = dt.astimezone(tz.gettz(provided_timezone))

            # check if the date is in the future, else invert
            if dt > datetime.now(tz.tzlocal()):
                dt = datetime.now(tz.tzlocal()) - (dt - datetime.now(tz.tzlocal()))

            return dt

        except (AttributeError, ValueError):
            log.exception('Failed parsing publishing date.')
