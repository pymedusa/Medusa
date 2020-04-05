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
        self,
        option_id=None,
        allowed=None,
        preferred=None,
        size_min=None,
        size_max=None,
        required_words=None,
        ignored_words=None,
        priority=None,
        db_row=None,
        profile=None
    ):
        if db_row:
            self.option_id = db_row['option_id']
            self.profile_id = db_row['quality_profile_id']
            self.allowed = db_row['allowed']
            self.preferred = db_row['preferred']
            self.size_min = db_row['size_min']
            self.size_max = db_row['size_max']
            self.priority = db_row['priority']

            self.required_words = db_row['rls_require_words']
            self.ignored_words = db_row['rls_ignore_words']
        else:
            self.option_id = option_id
            self.allowed = allowed
            self.preferred = preferred
            self.size_min = size_min
            self.size_max = size_max
            self.priority = priority
            self.required_words = required_words
            self.ignored_words = ignored_words
            self.profile = profile
            if self.profile:
                self.profile_id = self.profile.profile_id

    def save(self):
        """Save the QualityOption to db."""
        if self.profile:

            key_dict = {'option_id': self.option_id}

            value_dict = {
                'quality_profile_id': self.profile.profile_id,
                'allowed': self.allowed,
                'preferred': self.preferred,
                'size_min': self.size_min,
                'size_max': self.size_max,
                'priority': self.priority,
                'rls_require_words': self.required_words,
                'rls_ignore_words': self.ignored_words
            }
            self.profile.main_db.upsert('quality_profile_options', value_dict, key_dict)


class QualityProfile(object):
    """
    Quality profile class.

    Each profile can have multiple qualities, combined with ignored or required words, min and max size.
    When the property `qualities` is used, and the array has a length, the other properties like, quality, size_min, size_max
    are ignored.
    """
    def __init__(self, profile_id=None, description=None, enabled=False, default=False, qualities=None, quality=None):
        self.main_db = db.DBConnection()

        self.profile_id = profile_id
        self.description = description
        self.enabled = enabled
        self.default = default
        self.qualities = qualities or []
        self.quality = quality

        if not profile_id is None:
            self.load(profile_id)
        elif not qualities and quality:
            # Let's use the composed quality and generate quality options for migration purposes
            self._create_quality_options()

    def load(self, profile_id):
        """Load profile by id."""
        quality_profile = self.main_db.select(
            'SELECT * '
            'FROM quality_profiles'
        )

        if not quality_profile:
            raise Exception('Could not locate profile id with id: {0}'.format(profile_id))

        self.description = quality_profile[0]['description']
        self.enabled = quality_profile[0]['enabled']
        self.default = quality_profile[0]['defaultprofile']

        if len(quality_profile) > 0:
            quality_options = self.main_db.select(
                'SELECT * '
                'FROM quality_profile_options '
                'WHERE quality_profile_id = ?'
                , [profile_id]
            )

            for option in quality_options:
                self.qualities.append(QualityOption(db_row=option))

    def save(self):
        """Save current profile object."""
        key_dict = {'quality_profile_id': self.profile_id}

        value_dict = {
            'description': self.description,
            'enabled': self.enabled,
            'defaultprofile': self.default
        }
        result = self.main_db.upsert('quality_profiles', value_dict, key_dict)
        if result:
            self.profile_id = result.lastrowid

        # If there are qualities save them
        for quality in self.qualities:
            quality.save()

    def _create(self, db_row):
        """Create Quality Profile object."""
        pass

    def _create_quality_options(self):
        """Create QualityOptions from the composed quality."""
        allowed, preferred = Quality.split_quality(self.quality)
        priority = 1
        for quality in allowed:
            self.qualities.append(
                QualityOption(
                    allowed=quality,
                    priority=priority,
                    profile=self
                )
            )
            priority += 1

        priority = 1
        for quality in preferred:
            self.qualities.append(
                QualityOption(
                    preferred=quality,
                    priority=priority,
                    profile=self
                )
            )
            priority += 1

    @property
    def quality_allowed(self):
        """Combine all the allowed qualities from the self.qualities array."""
        return Quality.combine_qualities([quality.allowed for quality in self.qualities if quality.allowed], [])

    @property
    def quality_preferred(self):
        """Combine all the preferred qualities from the self.qualities array."""
        return Quality.combine_qualities([], [quality.preferred for quality in self.qualities if quality.preferred])

    @property
    def quality_composite(self):
        """Combine allowed and preferred qualities."""
        return Quality.combine_qualities(
            [quality.allowed for quality in self.qualities if quality.allowed],
            [quality.preferred for quality in self.qualities if quality.preferred]
        )
