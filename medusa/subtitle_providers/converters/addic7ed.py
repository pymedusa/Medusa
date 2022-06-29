# -*- coding: utf-8 -*-
"""Custom language converter for addic7ed."""
from babelfish import LanguageReverseConverter, language_converters


class Addic7edConverter(LanguageReverseConverter):
    """Addic7ed Converter class."""

    def __init__(self):
        """Converter constructor."""
        self.name_converter = language_converters['name']
        self.from_addic7ed = {
            'Català': ('cat',),
            'Chinese (Simplified)': ('zho',),
            'Chinese (Traditional)': ('zho',),
            'Euskera': ('eus',),
            'Galego': ('glg',),
            'Greek': ('ell',),
            'Malay': ('msa',),
            'Portuguese (Brazilian)': ('por', 'BR'),
            'Serbian (Cyrillic)': ('srp', None, 'Cyrl'),
            'Serbian (Latin)': ('srp',),
            'Spanish (Latin America)': ('spa',),
            'Spanish (Spain)': ('spa',),
            'French (Canadian)': ('fra', 'CA'),
        }
        self.to_addic7ed = {
            ('cat',): 'Català',
            ('zho',): 'Chinese (Simplified)',
            ('eus',): 'Euskera',
            ('glg',): 'Galego',
            ('ell',): 'Greek',
            ('msa',): 'Malay',
            ('por', 'BR'): 'Portuguese (Brazilian)',
            ('srp', None, 'Cyrl'): 'Serbian (Cyrillic)',
            ('fra', 'CA'): 'French (Canadian)',
        }
        self.codes = self.name_converter.codes | set(self.from_addic7ed.keys())

    def convert(self, alpha3, country=None, script=None):
        """Convert method."""
        if (alpha3, country, script) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country, script)]
        if (alpha3, country) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country)]
        if (alpha3,) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3,)]

        return self.name_converter.convert(alpha3, country, script)

    def reverse(self, addic7ed):
        """Reverse convert method."""
        if addic7ed in self.from_addic7ed:
            return self.from_addic7ed[addic7ed]

        return self.name_converter.reverse(addic7ed)
