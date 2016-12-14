# coding=utf-8
# Author: p0psicles
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
# pylint:disable=too-many-lines
"""String matcher class."""

import logging


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class StringMatcher(object):
    """Match a string against another, and tries to calculate a matching score.

    Initialize using your left side string. You can optionally provide a right side string. But this can also
    be overwritten using the fuzzy_compare() method.
    """
    def __init__(self, string_left, string_right=None, lower=True):
        """Initialize the StringMatcher.

        :param string_left: The left hand string.
        :param type string_left: str.
        :param string_right: Optionally add a right hand string.
        :param type string_right: str.
        :param lower: Optionally configure the StringMather to be case sensitive. lower = true will make it case
        sensitive.
        """
        self.string_left = string_left
        self.string_right = string_right
        self.score = 0
        self.score_avg = 0
        self.identical = False
        self.invalid_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '<', '>', '.', ',', '?', '/', '\\']
        self.lower = lower

    def _sanitize(self, str_sanitized):
        for in_char in self.invalid_chars:
            str_sanitized = str_sanitized.replace(in_char, '')
        str_sanitized = str_sanitized.strip()
        if self.lower:
            str_sanitized = str_sanitized.lower()
        return str_sanitized

    def fuzzy_compare(self, string_right=None):
        if not string_right and not self.string_right:
            raise Exception('You need to provide a right hand string.')

        str_left = self._sanitize(self.string_left)
        str_right = self._sanitize(string_right or self.string_right)

        log.debug('Going to compare string {0} with string {1}'.format(str_left, str_right))

        if str_left == str_right:
            self.score = self.score_avg = 100
            self.identical = True
            log.debug('Scored total of {0} points. Stings are identical.'.format(self.score))
            return self.score

        if len(str_left.split(' ')) == 1 and len(str_right.split(' ')) == 1:
            left_split = list(str_left)
            right_split = list(str_right)
        else:
            left_split = str_left.split(' ')
            right_split = str_right.split(' ')

        score_length = 25 - abs((len(left_split) - len(right_split)) * 10)
        log.debug('The strings segments differentiate {0} segments, scoring it with {1}'.
                  format(abs(len(left_split) - len(right_split)), score_length))

        score_random_match = 0
        score_pos_match = 0
        for segment_left in left_split:
            if segment_left in right_split:
                score_random_match += 40
                log.debug('Found segment_left {0} in {1}, scoring it +40'.format(segment_left, right_split))

            if str_left.find(segment_left) == str_right.find(segment_left) and str_right.find(segment_left) > -1:
                score_pos_match += 80
                log.debug('Found segment_left {0} in the exact same position as in right string. {1}, scoring it +50'.
                          format(segment_left, right_split))

        averaged_score_random_match = int(score_random_match / max(len(left_split), len(right_split)))
        averaged_score_pos_match = int(score_pos_match / max(len(left_split), len(right_split)))

        self.score_avg = int((score_length + averaged_score_random_match + averaged_score_pos_match) / 3)
        self.score = score_length + score_random_match + score_pos_match
        log.debug('Scored total of {0} points.'.format(self.score))

        return self.score_avg

    def fuzzy_compare_list(self, str_list):
        """Provide a list of strings, and compare your left hand string against this, using the fuzzy_compare()
        method.

        :param str_list: A list of strings, which you can compare your left hand string against.
        :returns: A dictionay with the highest result (score_avg). The object itself can be used to ask for more
        information, like self.score or self.identical.
        """
        results = []
        for cmp_string in str_list:
            score_avg = self.fuzzy_compare(cmp_string)
            if score_avg == 100 and [_ for _ in results if _['score_avg'] == 100]:
                raise Exception("Multiple exact matches. We don't want that!")

            results.append({'score_avg': score_avg,
                            'score': self.score,
                            'string_left': self.string_left,
                            'string_right': cmp_string,
                            'identical': self.identical})

        highest_rated = sorted(results, key=lambda k: float(k['score_avg']), reverse=True)[0]
        self.score = highest_rated['score']
        self.score_avg = highest_rated['score_avg']
        self.identical = highest_rated['identical']

        return highest_rated

