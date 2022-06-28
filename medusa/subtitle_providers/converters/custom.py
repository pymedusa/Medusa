# -*- coding: utf-8 -*-
"""Custom language converter used for parsing custom languages in subtitle files."""
from babelfish import LanguageReverseConverter, language_converters


class CustomConverter(LanguageReverseConverter):
    """Custom srt Converter class."""

    def __init__(self):
        """Converter constructor."""
        self.name_converter = language_converters['name']
        self.from_custom = {
            'Català': ('cat',),
            'Euskera': ('eus',),
            'Galego': ('glg',),
            'Greek': ('ell',),
            'Malay': ('msa',),
            'Danish': ('dan',),
        }
        self.to_custom = {
            ('cat',): 'Català',
            ('eus',): 'Euskera',
            ('glg',): 'Galego',
            ('ell',): 'Greek',
            ('msa',): 'Malay',
            ('dan',): 'Danish',
        }
        self.codes = self.name_converter.codes | set(self.from_custom.keys())

    def convert(self, alpha3, country=None, script=None):
        """Convert method."""
        if (alpha3, country, script) in self.to_custom:
            return self.to_custom[(alpha3, country, script)]
        if (alpha3, country) in self.to_custom:
            return self.to_custom[(alpha3, country)]
        if (alpha3,) in self.to_custom:
            return self.to_custom[(alpha3,)]

        return self.name_converter.convert(alpha3, country, script)

    def reverse(self, value):
        """Reverse convert method."""
        if value in self.from_custom:
            return self.from_custom[value]

        return self.name_converter.reverse(value)
