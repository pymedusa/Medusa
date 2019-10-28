"""Quality profile module."""

import logging
from medusa import app, db
from medusa.common import Quality
from medusa.logger.adapters.style import BraceAdapter


logger = BraceAdapter(logging.getLogger(__name__))
logger.logger.addHandler(logging.NullHandler())


class QualityOption(object):
    """Quality option object."""
    def __init__(
        self, profile_id=None,
             allowed=None,
             preferred=None,
             size_min=None,
             size_max=None,
             required_words=None,
             ignored_words=None,
             db_row=None
        ):
        if db_row:
            self.profile_id = db_row['quality_profile_id']
            self.allowed = db_row['quality_allowed']
            self.preferred = db_row['quality_preferred']
            self.size_min = db_row['size_min']
            self.size_max = db_row['size_max']

            self.required_words = db_row['rls_require_words']
            self.ignored_words = db_row['rls_ignore_words']
        else:
            self.profile_id = profile_id
            self.allowed = allowed
            self.preferred = preferred
            self.size_min = size_min
            self.size_max = size_max
            self.required_words = required_words
            self.ignored_words = ignored_words


class QualityProfile(object):
    """
    Quality profile class.

    Each profile can have multiple qualities, combined with ignored or required words, min and max size.
    When the property `qualities` is used, and the array has a length, the other properties like, quality, size_min, size_max
    are ignored.
    """
    def __init__(self, profile_id=None):
        self.main_db = db.DBConnection()

        self.profile_id = profile_id
        self.profile_description = None
        self.enabled = None
        self.default = None
        self.qualities = []
        self.quality = app.QUALITY_DEFAULT

        if not profile_id is None:
            self.load(profile_id)

    def load(self, profile_id):
        """Load profile by id."""
        main_db = db.DBConnection()
        quality_profile = main_db.select(
            'SELECT * '
            'FROM quality_profiles'
        )

        if not quality_profile:
            raise Exception('Could not locate profile id with id: {0}'.format(profile_id))

        self.profile_description = quality_profile[0]['description']
        self.enabled = quality_profile[0]['enabled']
        self.default = quality_profile[0]['default']

        if len(quality_profile) > 0:
            quality_options = main_db.select(
                'SELECT * '
                'FROM quality_profile_options '
                'WHERE quality_profile_id = ?'
                , [profile_id]
            )

            for option in quality_options:
                self.qualities.append(QualityOption(db_row=option))

    def save(self):
        """Save current profile object."""
        pass

    def _create(self, db_row):
        """Create Quality Profile object."""
        pass

    @property
    def quality_preferred(self):
        """Combine all the preferred qualities from the self.qualities array."""
        return Quality.combine_qualities([], [quality.preferred for quality in self.qualities if quality.preferred])

    @property
    def quality_allowed(self):
        """Combine all the allowed qualities from the self.qualities array."""
        return Quality.combine_qualities([quality.allowed for quality in self.qualities if quality.allowed], [])
