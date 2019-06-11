"""CSS matcher."""
from __future__ import unicode_literals
from datetime import datetime
from . import util
import re
from .import css_types as ct
import unicodedata

# Empty tag pattern (whitespace okay)
RE_NOT_EMPTY = re.compile('[^ \t\r\n\f]')

RE_NOT_WS = re.compile('[^ \t\r\n\f]+')

# Relationships
REL_PARENT = ' '
REL_CLOSE_PARENT = '>'
REL_SIBLING = '~'
REL_CLOSE_SIBLING = '+'

# Relationships for :has() (forward looking)
REL_HAS_PARENT = ': '
REL_HAS_CLOSE_PARENT = ':>'
REL_HAS_SIBLING = ':~'
REL_HAS_CLOSE_SIBLING = ':+'

NS_XHTML = 'http://www.w3.org/1999/xhtml'

DIR_FLAGS = ct.SEL_DIR_LTR | ct.SEL_DIR_RTL
RANGES = ct.SEL_IN_RANGE | ct.SEL_OUT_OF_RANGE

DIR_MAP = {
    'ltr': ct.SEL_DIR_LTR,
    'rtl': ct.SEL_DIR_RTL,
    'auto': 0
}

RE_NUM = re.compile(r"^(?P<value>-?(?:[0-9]{1,}(\.[0-9]+)?|\.[0-9]+))$")
RE_TIME = re.compile(r'^(?P<hour>[0-9]{2}):(?P<minutes>[0-9]{2})$')
RE_MONTH = re.compile(r'^(?P<year>[0-9]{4,})-(?P<month>[0-9]{2})$')
RE_WEEK = re.compile(r'^(?P<year>[0-9]{4,})-W(?P<week>[0-9]{2})$')
RE_DATE = re.compile(r'^(?P<year>[0-9]{4,})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})$')
RE_DATETIME = re.compile(
    r'^(?P<year>[0-9]{4,})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})T(?P<hour>[0-9]{2}):(?P<minutes>[0-9]{2})$'
)

MONTHS_30 = (4, 6, 9, 11)  # April, June, September, and November
FEB = 2
SHORT_MONTH = 30
LONG_MONTH = 31
FEB_MONTH = 28
FEB_LEAP_MONTH = 29
DAYS_IN_WEEK = 7


def assert_valid_input(tag):
    """Check if valid input tag."""

    # Fail on unexpected types.
    if not util.is_tag(tag):
        raise TypeError("Expected a BeautifulSoup 'Tag', but instead recieved type {}".format(type(tag)))


def get_comments(el, limit=0):
    """Get comments."""

    assert_valid_input(el)

    if limit < 1:
        limit = None

    for child in el.descendants:
        if util.is_comment(child):
            yield child
            if limit is not None:
                limit -= 1
                if limit < 1:
                    break


class FakeNthParent(object):
    """
    Fake parent for `nth` selector.

    When we have a fragment with no `BeautifulSoup` document object,
    we can't evaluate `nth` selectors properly.  Create a temporary
    fake parent so we can traverse the root element as a child.
    """

    def __init__(self, element):
        """Initialize."""

        self.contents = [element]


class CSSMatch(object):
    """Perform CSS matching."""

    def __init__(self, selectors, scope, namespaces, flags):
        """Initialize."""

        assert_valid_input(scope)
        self.tag = scope
        self.cached_meta_lang = None
        self.cached_default_forms = []
        self.cached_indeterminate_forms = []
        self.selectors = selectors
        self.namespaces = namespaces
        self.flags = flags
        doc = scope
        while doc.parent:
            doc = doc.parent
        root = None
        if not util.is_doc(doc):
            root = doc
        else:
            for child in doc.children:
                if util.is_tag(child):
                    root = child
                    break
        self.root = root
        self.scope = scope if scope is not doc else root
        self.html_namespace = self.is_html_ns(root)
        self.is_xml = doc._is_xml and not self.html_namespace

    def is_html_ns(self, el):
        """Check if in HTML namespace."""

        ns = getattr(el, 'namespace') if el else None
        return ns and ns == NS_XHTML

    def get_namespace(self, el):
        """Get the namespace for the element."""

        namespace = ''
        ns = el.namespace
        if ns:
            namespace = ns
        return namespace

    def supports_namespaces(self):
        """Check if namespaces are supported in the HTML type."""

        return self.is_xml or self.html_namespace

    def get_bidi(self, el):
        """Get directionality from element text."""

        for node in el.children:

            # Analyze child text nodes
            if util.is_tag(node):

                # Avoid analyzing certain elements specified in the specification.
                direction = DIR_MAP.get(util.lower(node.attrs.get('dir', '')), None)
                if (
                    util.lower(node.name) in ('bdi', 'script', 'style', 'textarea') or
                    direction is not None
                ):
                    continue  # pragma: no cover

                # Check directionality of this node's text
                value = self.get_bidi(node)
                if value is not None:
                    return value

                # Direction could not be determined
                continue  # pragma: no cover

            # Skip `doctype` comments, etc.
            if util.is_special_string(node):
                continue

            # Analyze text nodes for directionality.
            for c in node:
                bidi = unicodedata.bidirectional(c)
                if bidi in ('AL', 'R', 'L'):
                    return ct.SEL_DIR_LTR if bidi == 'L' else ct.SEL_DIR_RTL
        return None

    def get_attribute(self, el, attr, prefix):
        """Get attribute from element if it exists."""

        value = None
        if self.supports_namespaces():
            value = None
            # If we have not defined namespaces, we can't very well find them, so don't bother trying.
            if prefix:
                ns = self.namespaces.get(prefix)
                if ns is None and prefix != '*':
                    return None
            else:
                ns = None

            for k, v in el.attrs.items():

                # Get attribute parts
                namespace = getattr(k, 'namespace', None)
                name = getattr(k, 'name', None)

                # Can't match a prefix attribute as we haven't specified one to match
                # Try to match it normally as a whole `p:a` as selector may be trying `p\:a`.
                if ns is None:
                    if (self.is_xml and attr == k) or (not self.is_xml and util.lower(attr) == util.lower(k)):
                        value = v
                        break
                    # Coverage is not finding this even though it is executed.
                    # Adding a print statement before this (and erasing coverage) causes coverage to find the line.
                    # Ignore the false positive message.
                    continue  # pragma: no cover

                # We can't match our desired prefix attribute as the attribute doesn't have a prefix
                if namespace is None or ns != namespace and prefix != '*':
                    continue

                if self.is_xml:
                    # The attribute doesn't match.
                    if attr != name:
                        continue
                else:
                    # The attribute doesn't match.
                    if util.lower(attr) != util.lower(name):
                        continue
                value = v
                break
        else:
            for k, v in el.attrs.items():
                if util.lower(attr) != util.lower(k):
                    continue
                value = v
                break
        return value

    def get_classes(self, el):
        """Get classes."""

        classes = el.attrs.get('class', [])
        if isinstance(classes, util.ustr):
            classes = RE_NOT_WS.findall(classes)
        return classes

    def get_attribute_by_name(self, el, name, default=None):
        """Get attribute by name."""

        value = default
        for k, v in el.attrs.items():
            if (k if self.is_xml else util.lower(k)) == name:
                value = v
                break
        return value

    def validate_day(self, year, month, day):
        """Validate day."""

        max_days = LONG_MONTH
        if month == FEB:
            max_days = FEB_LEAP_MONTH if ((year % 4 == 0) and (year % 100 != 0)) or (year % 400 == 0) else FEB_MONTH
        elif month in MONTHS_30:
            max_days = SHORT_MONTH
        return 1 <= day <= max_days

    def validate_week(self, year, week):
        """Validate week."""

        max_week = datetime.strptime("{}-{}-{}".format(12, 31, year), "%m-%d-%Y").isocalendar()[1]
        if max_week == 1:
            max_week = 53
        return 1 <= week <= max_week

    def validate_month(self, month):
        """Validate month."""

        return 1 <= month <= 12

    def validate_year(self, year):
        """Validate year."""

        return 1 <= year

    def validate_hour(self, hour):
        """Validate hour."""

        return 0 <= hour <= 23

    def validate_minutes(self, minutes):
        """Validate minutes."""

        return 0 <= minutes <= 59

    def parse_input_value(self, itype, value):
        """Parse the input value."""

        parsed = None
        if itype == "date":
            m = RE_DATE.match(value)
            if m:
                year = int(m.group('year'), 10)
                month = int(m.group('month'), 10)
                day = int(m.group('day'), 10)
                if self.validate_year(year) and self.validate_month(month) and self.validate_day(year, month, day):
                    parsed = (year, month, day)
        elif itype == "month":
            m = RE_MONTH.match(value)
            if m:
                year = int(m.group('year'), 10)
                month = int(m.group('month'), 10)
                if self.validate_year(year) and self.validate_month(month):
                    parsed = (year, month)
        elif itype == "week":
            m = RE_WEEK.match(value)
            if m:
                year = int(m.group('year'), 10)
                week = int(m.group('week'), 10)
                if self.validate_year(year) and self.validate_week(year, week):
                    parsed = (year, week)
        elif itype == "time":
            m = RE_TIME.match(value)
            if m:
                hour = int(m.group('hour'), 10)
                minutes = int(m.group('minutes'), 10)
                if self.validate_hour(hour) and self.validate_minutes(minutes):
                    parsed = (hour, minutes)
        elif itype == "datetime-local":
            m = RE_DATETIME.match(value)
            if m:
                year = int(m.group('year'), 10)
                month = int(m.group('month'), 10)
                day = int(m.group('day'), 10)
                hour = int(m.group('hour'), 10)
                minutes = int(m.group('minutes'), 10)
                if (
                    self.validate_year(year) and self.validate_month(month) and self.validate_day(year, month, day) and
                    self.validate_hour(hour) and self.validate_minutes(minutes)
                ):
                    parsed = (year, month, day, hour, minutes)
        elif itype in ("number", "range"):
            m = RE_NUM.match(value)
            if m:
                parsed = float(m.group('value'))
        return parsed

    def match_namespace(self, el, tag):
        """Match the namespace of the element."""

        match = True
        namespace = self.get_namespace(el)
        default_namespace = self.namespaces.get('')
        tag_ns = '' if tag.prefix is None else self.namespaces.get(tag.prefix, None)
        # We must match the default namespace if one is not provided
        if tag.prefix is None and (default_namespace is not None and namespace != default_namespace):
            match = False
        # If we specified `|tag`, we must not have a namespace.
        elif (tag.prefix is not None and tag.prefix == '' and namespace):
            match = False
        # Verify prefix matches
        elif (
            tag.prefix and
            tag.prefix != '*' and (tag_ns is None or namespace != tag_ns)
        ):
            match = False
        return match

    def match_attributes(self, el, attributes):
        """Match attributes."""

        match = True
        if attributes:
            for a in attributes:
                value = self.get_attribute(el, a.attribute, a.prefix)
                pattern = a.xml_type_pattern if not self.html_namespace and a.xml_type_pattern else a.pattern
                if isinstance(value, list):
                    value = ' '.join(value)
                if value is None:
                    match = False
                    break
                elif pattern is None:
                    continue
                elif pattern.match(value) is None:
                    match = False
                    break
        return match

    def match_tagname(self, el, tag):
        """Match tag name."""

        return not (
            tag.name and
            tag.name not in ((util.lower(el.name) if not self.is_xml else el.name), '*')
        )

    def match_tag(self, el, tag):
        """Match the tag."""

        has_ns = self.supports_namespaces()
        match = True
        if tag is not None:
            # Verify namespace
            if has_ns and not self.match_namespace(el, tag):
                match = False
            if not self.match_tagname(el, tag):
                match = False
        return match

    def match_past_relations(self, el, relation):
        """Match past relationship."""

        found = False
        if relation[0].rel_type == REL_PARENT:
            parent = el.parent
            while not found and parent:
                found = self.match_selectors(parent, relation)
                parent = parent.parent
        elif relation[0].rel_type == REL_CLOSE_PARENT:
            parent = el.parent
            if parent:
                found = self.match_selectors(parent, relation)
        elif relation[0].rel_type == REL_SIBLING:
            sibling = el.previous_sibling
            while not found and sibling:
                if not util.is_tag(sibling):
                    sibling = sibling.previous_sibling
                    continue
                found = self.match_selectors(sibling, relation)
                sibling = sibling.previous_sibling
        elif relation[0].rel_type == REL_CLOSE_SIBLING:
            sibling = el.previous_sibling
            while sibling and not util.is_tag(sibling):
                sibling = sibling.previous_sibling
            if sibling and util.is_tag(sibling):
                found = self.match_selectors(sibling, relation)
        return found

    def match_future_child(self, parent, relation, recursive=False):
        """Match future child."""

        match = False
        for child in (parent.descendants if recursive else parent.children):
            if not util.is_tag(child):
                continue
            match = self.match_selectors(child, relation)
            if match:
                break
        return match

    def match_future_relations(self, el, relation):
        """Match future relationship."""

        found = False
        if relation[0].rel_type == REL_HAS_PARENT:
            found = self.match_future_child(el, relation, True)
        elif relation[0].rel_type == REL_HAS_CLOSE_PARENT:
            found = self.match_future_child(el, relation)
        elif relation[0].rel_type == REL_HAS_SIBLING:
            sibling = el.next_sibling
            while not found and sibling:
                if not util.is_tag(sibling):
                    sibling = sibling.next_sibling
                    continue
                found = self.match_selectors(sibling, relation)
                sibling = sibling.next_sibling
        elif relation[0].rel_type == REL_HAS_CLOSE_SIBLING:
            sibling = el.next_sibling
            while sibling and not util.is_tag(sibling):
                sibling = sibling.next_sibling
            if sibling and util.is_tag(sibling):
                found = self.match_selectors(sibling, relation)
        return found

    def match_relations(self, el, relation):
        """Match relationship to other elements."""

        found = False

        if relation[0].rel_type.startswith(':'):
            found = self.match_future_relations(el, relation)
        else:
            found = self.match_past_relations(el, relation)

        return found

    def match_id(self, el, ids):
        """Match element's ID."""

        found = True
        for i in ids:
            if i != el.attrs.get('id', ''):
                found = False
                break
        return found

    def match_classes(self, el, classes):
        """Match element's classes."""

        current_classes = self.get_classes(el)
        found = True
        for c in classes:
            if c not in current_classes:
                found = False
                break
        return found

    def match_root(self, el):
        """Match element as root."""

        return self.root and self.root is el

    def match_scope(self, el):
        """Match element as scope."""

        return self.scope is el

    def match_nth_tag_type(self, el, child):
        """Match tag type for `nth` matches."""

        return(
            (child.name == (util.lower(el.name) if not self.is_xml else el.name)) and
            (not self.supports_namespaces() or self.get_namespace(child) == self.get_namespace(el))
        )

    def match_nth(self, el, nth):
        """Match `nth` elements."""

        matched = True

        for n in nth:
            matched = False
            if n.selectors and not self.match_selectors(el, n.selectors):
                break
            parent = el.parent
            if parent is None:
                parent = FakeNthParent(el)
            last = n.last
            last_index = len(parent.contents) - 1
            relative_index = 0
            a = n.a
            b = n.b
            var = n.n
            count = 0
            count_incr = 1
            factor = -1 if last else 1
            index = len(parent.contents) - 1 if last else 0
            idx = last_idx = a * count + b if var else a

            # We can only adjust bounds within a variable index
            if var:
                # Abort if our nth index is out of bounds and only getting further out of bounds as we increment.
                # Otherwise, increment to try to get in bounds.
                adjust = None
                while idx < 1 or idx > last_index:
                    if idx < 0:
                        diff_low = 0 - idx
                        if adjust is not None and adjust == 1:
                            break
                        adjust = -1
                        count += count_incr
                        idx = last_idx = a * count + b if var else a
                        diff = 0 - idx
                        if diff >= diff_low:
                            break
                    else:
                        diff_high = idx - last_index
                        if adjust is not None and adjust == -1:
                            break
                        adjust = 1
                        count += count_incr
                        idx = last_idx = a * count + b if var else a
                        diff = idx - last_index
                        if diff >= diff_high:
                            break
                        diff_high = diff

                # If a < 0, our count is working backwards, so floor the index by increasing the count.
                # Find the count that yields the lowest, in bound value and use that.
                # Lastly reverse count increment so that we'll increase our index.
                lowest = count
                if a < 0:
                    while idx >= 1:
                        lowest = count
                        count += count_incr
                        idx = last_idx = a * count + b if var else a
                    count_incr = -1
                count = lowest
                idx = last_idx = a * count + b if var else a

            # Evaluate elements while our calculated nth index is still in range
            while 1 <= idx <= last_index + 1:
                child = None
                # Evaluate while our child index is still in range.
                while 0 <= index <= last_index:
                    child = parent.contents[index]
                    index += factor
                    if not util.is_tag(child):
                        continue
                    # Handle `of S` in `nth-child`
                    if n.selectors and not self.match_selectors(child, n.selectors):
                        continue
                    # Handle `of-type`
                    if n.of_type and not self.match_nth_tag_type(el, child):
                        continue
                    relative_index += 1
                    if relative_index == idx:
                        if child is el:
                            matched = True
                        else:
                            break
                    if child is el:
                        break
                if child is el:
                    break
                last_idx = idx
                count += count_incr
                if count < 0:
                    # Count is counting down and has now ventured into invalid territory.
                    break
                idx = a * count + b if var else a
                if last_idx == idx:
                    break
            if not matched:
                break
        return matched

    def match_empty(self, el):
        """Check if element is empty (if requested)."""

        is_empty = True
        for child in el.children:
            if util.is_tag(child):
                is_empty = False
                break
            elif (
                (util.is_navigable_string(child) and not util.is_special_string(child)) and
                RE_NOT_EMPTY.search(child)
            ):
                is_empty = False
                break
        return is_empty

    def match_subselectors(self, el, selectors):
        """Match selectors."""

        match = True
        for sel in selectors:
            if not self.match_selectors(el, sel):
                match = False
        return match

    def match_contains(self, el, contains):
        """Match element if it contains text."""

        types = (util.get_navigable_string_type(el),)
        match = True
        for c in contains:
            if c not in el.get_text(types=types):
                match = False
                break
        return match

    def match_default(self, el):
        """Match default."""

        match = False

        # Find this input's form
        form = None
        parent = el.parent
        while parent and form is None:
            if util.lower(parent.name) == 'form':
                form = parent
            else:
                parent = parent.parent

        # Look in form cache to see if we've already located its default button
        found_form = False
        for f, t in self.cached_default_forms:
            if f is form:
                found_form = True
                if t is el:
                    match = True
                break

        # We didn't have the form cached, so look for its default button
        if not found_form:
            child_found = False
            for child in form.descendants:
                if not util.is_tag(child):
                    continue
                name = util.lower(child.name)
                # Can't do nested forms (haven't figured out why we never hit this)
                if name == 'form':  # pragma: no cover
                    break
                if name in ('input', 'button'):
                    for k, v in child.attrs.items():
                        if util.lower(k) == 'type' and util.lower(v) == 'submit':
                            child_found = True
                            self.cached_default_forms.append([form, child])
                            if el is child:
                                match = True
                            break
                if child_found:
                    break
        return match

    def match_indeterminate(self, el):
        """Match default."""

        match = False
        name = el.attrs.get('name')

        def get_parent_form(el):
            """Find this input's form."""
            form = None
            parent = el.parent
            while form is None:
                if util.lower(parent.name) == 'form':
                    form = parent
                    break
                elif parent.parent:
                    parent = parent.parent
                else:
                    form = parent
                    break
            return form

        form = get_parent_form(el)

        # Look in form cache to see if we've already evaluated that its fellow radio buttons are indeterminate
        found_form = False
        for f, n, i in self.cached_indeterminate_forms:
            if f is form and n == name:
                found_form = True
                if i is True:
                    match = True
                break

        # We didn't have the form cached, so validate that the radio button is indeterminate
        if not found_form:
            checked = False
            for child in form.descendants:
                if not util.is_tag(child) or child is el:
                    continue
                tag_name = util.lower(child.name)
                if tag_name == 'input':
                    is_radio = False
                    check = False
                    has_name = False
                    for k, v in child.attrs.items():
                        if util.lower(k) == 'type' and util.lower(v) == 'radio':
                            is_radio = True
                        elif util.lower(k) == 'name' and v == name:
                            has_name = True
                        elif util.lower(k) == 'checked':
                            check = True
                        if is_radio and check and has_name and get_parent_form(child) is form:
                            checked = True
                            break
                if checked:
                    break
            if not checked:
                match = True
            self.cached_indeterminate_forms.append([form, name, match])

        return match

    def match_lang(self, el, langs):
        """Match languages."""

        match = False
        has_ns = self.supports_namespaces()

        # Walk parents looking for `lang` (HTML) or `xml:lang` XML property.
        parent = el
        found_lang = None
        while parent and parent.parent and not found_lang:
            ns = self.is_html_ns(parent)
            for k, v in parent.attrs.items():
                if (
                    (self.is_xml and k == 'xml:lang') or
                    (
                        not self.is_xml and (
                            ((not has_ns or ns) and util.lower(k) == 'lang') or
                            (has_ns and not ns and util.lower(k) == 'xml:lang')
                        )
                    )
                ):
                    found_lang = v
                    break
            parent = parent.parent

        # Use cached meta language.
        if not found_lang and self.cached_meta_lang is not None:
            found_lang = self.cached_meta_lang

        # If we couldn't find a language, and the document is HTML, look to meta to determine language.
        if found_lang is None and not self.is_xml:
            # Find head
            found = False
            for tag in ('html', 'head'):
                found = False
                for child in parent.children:
                    if util.is_tag(child) and util.lower(child.name) == tag:
                        found = True
                        parent = child
                        break
                if not found:  # pragma: no cover
                    break

            # Search meta tags
            if found:
                for child in parent:
                    if util.is_tag(child) and util.lower(child.name) == 'meta':
                        c_lang = False
                        content = None
                        for k, v in child.attrs.items():
                            if util.lower(k) == 'http-equiv' and util.lower(v) == 'content-language':
                                c_lang = True
                            if util.lower(k) == 'content':
                                content = v
                            if c_lang and content:
                                found_lang = content
                                self.cached_meta_lang = found_lang
                                break
                    if found_lang:
                        break
                if not found_lang:
                    self.cached_meta_lang = False

        # If we determined a language, compare.
        if found_lang:
            for patterns in langs:
                match = False
                for pattern in patterns:
                    if pattern.match(found_lang):
                        match = True
                if not match:
                    break

        return match

    def match_dir(self, el, directionality):
        """Check directionality."""

        # If we have to match both left and right, we can't match either.
        if directionality & ct.SEL_DIR_LTR and directionality & ct.SEL_DIR_RTL:
            return False

        # Element has defined direction of left to right or right to left
        direction = DIR_MAP.get(util.lower(el.attrs.get('dir', '')), None)
        if direction not in (None, 0):
            return direction == directionality

        # Element is the document element (the root) and no direction assigned, assume left to right.
        is_root = self.match_root(el)
        if is_root and direction is None:
            return ct.SEL_DIR_LTR == directionality

        # If `input[type=telephone]` and no direction is assigned, assume left to right.
        is_input = util.lower(el.name) == 'input'
        is_textarea = util.lower(el.name) == 'textarea'
        is_bdi = util.lower(el.name) == 'bdi'
        itype = util.lower(self.get_attribute_by_name(el, 'type', '')) if is_input else ''
        if is_input and itype == 'tel' and direction is None:
            return ct.SEL_DIR_LTR == directionality

        # Auto handling for text inputs
        if ((is_input and itype in ('text', 'search', 'tel', 'url', 'email')) or is_textarea) and direction == 0:
            if is_textarea:
                value = []
                for node in el.contents:
                    if util.is_navigable_string(node) and not util.is_special_string(node):
                        value.append(node)
                value = ''.join(value)
            else:
                value = self.get_attribute_by_name(el, 'value', '')
            if value:
                for c in value:
                    bidi = unicodedata.bidirectional(c)
                    if bidi in ('AL', 'R', 'L'):
                        direction = ct.SEL_DIR_LTR if bidi == 'L' else ct.SEL_DIR_RTL
                        return direction == directionality
                # Assume left to right
                return ct.SEL_DIR_LTR == directionality
            elif is_root:
                return ct.SEL_DIR_LTR == directionality
            return self.match_dir(el.parent, directionality)

        # Auto handling for `bdi` and other non text inputs.
        if (is_bdi and direction is None) or direction == 0:
            direction = self.get_bidi(el)
            if direction is not None:
                return direction == directionality
            elif is_root:
                return ct.SEL_DIR_LTR == directionality
            return self.match_dir(el.parent, directionality)

        # Match parents direction
        return self.match_dir(el.parent, directionality)

    def match_range(self, el, condition):
        """
        Match range.

        Behavior is modeled after what we see in browsers. Browsers seem to evaluate
        if the value is out of range, and if not, it is in range. So a missing value
        will not evaluate out of range; therefore, value is in range. Personally, I
        feel like this should evaluate as neither in or out of range.
        """

        out_of_range = False

        itype = self.get_attribute_by_name(el, 'type').lower()
        mn = self.get_attribute_by_name(el, 'min', None)
        if mn is not None:
            mn = self.parse_input_value(itype, mn)
        mx = self.get_attribute_by_name(el, 'max', None)
        if mx is not None:
            mx = self.parse_input_value(itype, mx)

        # There is no valid min or max, so we cannot evaluate a range
        if mn is None and mx is None:
            return False

        value = self.get_attribute_by_name(el, 'value', None)
        if value is not None:
            value = self.parse_input_value(itype, value)
        if value is not None:
            if itype in ("date", "datetime-local", "month", "week", "number", "range"):
                if mn is not None and value < mn:
                    out_of_range = True
                if not out_of_range and mx is not None and value > mx:
                    out_of_range = True
            elif itype == "time":
                if mn is not None and mx is not None and mn > mx:
                    # Time is periodic, so this is a reversed/discontinuous range
                    if value < mn and value > mx:
                        out_of_range = True
                else:
                    if mn is not None and value < mn:
                        out_of_range = True
                    if not out_of_range and mx is not None and value > mx:
                        out_of_range = True

        return not out_of_range if condition & ct.SEL_IN_RANGE else out_of_range

    def match_defined(self, el):
        """
        Match defined.

        `:defined` is related to custom elements in a browser.

        - If the document is XML (not XHTML), all tags will match.
        - Tags that are not custom (don't have a hyphen) are marked defined.
        - If the tag has a prefix (without or without a namespace), it will not match.

        This is of course requires the parser to provide us with the proper prefix and namespace info,
        if it doesn't, there is nothing we can do.
        """

        return (
            self.is_xml or
            el.name.find('-') == -1 or
            el.name.find(':') != -1 or
            el.prefix is not None
        )

    def match_selectors(self, el, selectors):
        """Check if element matches one of the selectors."""

        match = False
        is_not = selectors.is_not
        is_html = selectors.is_html
        if not (is_html and self.is_xml):
            for selector in selectors:
                match = is_not
                # We have a un-matchable situation (like `:focus` as you can focus an element in this environment)
                if isinstance(selector, ct.NullSelector):
                    continue
                # Verify tag matches
                if not self.match_tag(el, selector.tag):
                    continue
                # Verify tag is defined
                if selector.flags & ct.SEL_DEFINED and not self.match_defined(el):
                    continue
                # Verify element is root
                if selector.flags & ct.SEL_ROOT and not self.match_root(el):
                    continue
                # Verify element is scope
                if selector.flags & ct.SEL_SCOPE and not self.match_scope(el):
                    continue
                # Verify `nth` matches
                if not self.match_nth(el, selector.nth):
                    continue
                if selector.flags & ct.SEL_EMPTY and not self.match_empty(el):
                    continue
                # Verify id matches
                if selector.ids and not self.match_id(el, selector.ids):
                    continue
                # Verify classes match
                if selector.classes and not self.match_classes(el, selector.classes):
                    continue
                # Verify attribute(s) match
                if not self.match_attributes(el, selector.attributes):
                    continue
                # Verify ranges
                if selector.flags & RANGES and not self.match_range(el, selector.flags & RANGES):
                    continue
                # Verify language patterns
                if selector.lang and not self.match_lang(el, selector.lang):
                    continue
                # Verify pseudo selector patterns
                if selector.selectors and not self.match_subselectors(el, selector.selectors):
                    continue
                # Verify relationship selectors
                if selector.relation and not self.match_relations(el, selector.relation):
                    continue
                # Validate that the current default selector match corresponds to the first submit button in the form
                if selector.flags & ct.SEL_DEFAULT and not self.match_default(el):
                    continue
                # Validate that the unset radio button is among radio buttons with the same name in a form that are
                # also not set.
                if selector.flags & ct.SEL_INDETERMINATE and not self.match_indeterminate(el):
                    continue
                # Validate element directionality
                if selector.flags & DIR_FLAGS and not self.match_dir(el, selector.flags & DIR_FLAGS):
                    continue
                # Validate that the tag contains the specified text.
                if not self.match_contains(el, selector.contains):
                    continue
                match = not is_not
                break

        return match

    def select(self, limit=0):
        """Match all tags under the targeted tag."""

        if limit < 1:
            limit = None

        for child in self.tag.descendants:
            if util.is_tag(child) and self.match(child):
                yield child
                if limit is not None:
                    limit -= 1
                    if limit < 1:
                        break

    def closest(self):
        """Match closest ancestor."""

        current = self.tag
        closest = None
        while closest is None and current is not None:
            if self.match(current):
                closest = current
            else:
                current = current.parent
        return closest

    def filter(self):  # noqa A001
        """Filter tag's children."""

        return [node for node in self.tag if not util.is_navigable_string(node) and self.match(node)]

    def match(self, el):
        """Match."""

        return not util.is_doc(el) and util.is_tag(el) and self.match_selectors(el, self.selectors)


class SoupSieve(ct.Immutable):
    """Compiled Soup Sieve selector matching object."""

    __slots__ = ("pattern", "selectors", "namespaces", "flags", "_hash")

    def __init__(self, pattern, selectors, namespaces, flags):
        """Initialize."""

        super(SoupSieve, self).__init__(
            pattern=pattern,
            selectors=selectors,
            namespaces=namespaces,
            flags=flags
        )

    def match(self, tag):
        """Match."""

        return CSSMatch(self.selectors, tag, self.namespaces, self.flags).match(tag)

    def closest(self, tag):
        """Match closest ancestor."""

        return CSSMatch(self.selectors, tag, self.namespaces, self.flags).closest()

    def filter(self, iterable):  # noqa A001
        """
        Filter.

        `CSSMatch` can cache certain searches for tags of the same document,
        so if we are given a tag, all tags are from the same document,
        and we can take advantage of the optimization.

        Any other kind of iterable could have tags from different documents or detached tags,
        so for those, we use a new `CSSMatch` for each item in the iterable.
        """

        if util.is_tag(iterable):
            return CSSMatch(self.selectors, iterable, self.namespaces, self.flags).filter()
        else:
            return [node for node in iterable if not util.is_navigable_string(node) and self.match(node)]

    def comments(self, tag, limit=0):
        """Get comments only."""

        return list(self.icomments(tag, limit))

    def icomments(self, tag, limit=0):
        """Iterate comments only."""

        for comment in get_comments(tag, limit):
            yield comment

    def select_one(self, tag):
        """Select a single tag."""

        tags = self.select(tag, limit=1)
        return tags[0] if tags else None

    def select(self, tag, limit=0):
        """Select the specified tags."""

        return list(self.iselect(tag, limit))

    def iselect(self, tag, limit=0):
        """Iterate the specified tags."""

        for el in CSSMatch(self.selectors, tag, self.namespaces, self.flags).select(limit):
            yield el

    def __repr__(self):  # pragma: no cover
        """Representation."""

        return "SoupSieve(pattern={!r}, namespaces={!r}, flags={!r})".format(self.pattern, self.namespaces, self.flags)

    __str__ = __repr__


ct.pickle_register(SoupSieve)
