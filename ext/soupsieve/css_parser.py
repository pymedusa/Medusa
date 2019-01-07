"""CSS selector parser."""
from __future__ import unicode_literals
import re
from . import util
from . import css_match as cm
from . import css_types as ct
from collections import OrderedDict

# Simple pseudo classes that take no parameters
PSEUDO_SIMPLE = {
    ":any-link",
    ":empty",
    ":first-child",
    ":first-of-type",
    ":last-child",
    ":last-of-type",
    ":link",
    ":only-child",
    ":only-of-type",
    ":root",
    ':checked',
    ':default',
    ':disabled',
    ':enabled',
    ':indeterminate',
    ':optional',
    ':placeholder-shown',
    ':read-only',
    ':read-write',
    ':required',
    ':scope'
}

# Supported, simple pseudo classes that match nothing in the Soup Sieve environment
PSEUDO_SIMPLE_NO_MATCH = {
    ':active',
    ':current',
    ':focus',
    ':focus-visible',
    ':focus-within',
    ':future',
    ':host',
    ':hover',
    ':local-link',
    ':past',
    ':paused',
    ':playing',
    ':target',
    ':target-within',
    ':user-invalid',
    ':visited'
}

# Complex pseudo classes that take selector lists
PSEUDO_COMPLEX = {
    ':contains',
    ':has',
    ':is',
    ':matches',
    ':not',
    ':where'
}

PSEUDO_COMPLEX_NO_MATCH = {
    ':current',
    ':host',
    ':host-context'
}

# Complex pseudo classes that take very specific parameters and are handled special
PSEUDO_SPECIAL = {
    ':dir',
    ':lang',
    ':nth-child',
    ':nth-last-child',
    ':nth-last-of-type',
    ':nth-of-type'
}

PSEUDO_SUPPORTED = PSEUDO_SIMPLE | PSEUDO_SIMPLE_NO_MATCH | PSEUDO_COMPLEX | PSEUDO_COMPLEX_NO_MATCH | PSEUDO_SPECIAL

# Sub-patterns parts
# Whitespace
WS = r'[ \t\r\n\f]'
# Comments
COMMENTS = r'(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)'
# Whitespace with comments included
WSC = r'(?:{ws}|{comments})'.format(ws=WS, comments=COMMENTS)
# CSS escapes
CSS_ESCAPES = r'(?:\\[a-f0-9]{{1,6}}{ws}?|\\[^\r\n\f])'.format(ws=WS)
# CSS Identifier
IDENTIFIER = r'(?:(?!-?[0-9]|--)(?:[^\x00-\x2c\x2e\x2f\x3A-\x40\x5B-\x5E\x60\x7B-\x9f]|{esc})+)'.format(esc=CSS_ESCAPES)
# `nth` content
NTH = r'(?:[-+])?(?:[0-9]+n?|n)(?:(?<=n){ws}*(?:[-+]){ws}*(?:[0-9]+))?'.format(ws=WSC)
# Value: quoted string or identifier
VALUE = r'''(?:"(?:\\.|[^\\"]+)*?"|'(?:\\.|[^\\']+)*?'|{ident}+)'''.format(ident=IDENTIFIER)
# Attribute value comparison. `!=` is handled special as it is non-standard.
ATTR = r'''
(?:{ws}*(?P<cmp>[!~^|*$]?=){ws}*(?P<value>{value})(?:{ws}+(?P<case>[is]))?)?{ws}*\]
'''.format(ws=WSC, value=VALUE)

# Selector patterns
# IDs (`#id`)
PAT_ID = r'\#{ident}'.format(ident=IDENTIFIER)
# Classes (`.class`)
PAT_CLASS = r'\.{ident}'.format(ident=IDENTIFIER)
# Prefix:Tag (`prefix|tag`)
PAT_TAG = r'(?:(?:{ident}|\*)?\|)?(?:{ident}|\*)'.format(ident=IDENTIFIER)
# Attributes (`[attr]`, `[attr=value]`, etc.)
PAT_ATTR = r'\[{ws}*(?P<ns_attr>(?:(?:{ident}|\*)?\|)?{ident}){attr}'.format(ws=WSC, ident=IDENTIFIER, attr=ATTR)
# Pseudo class (`:pseudo-class`, `:pseudo-class(`)
PAT_PSEUDO_CLASS = r'(?P<name>:{ident}+)(?P<open>\({ws}*)?'.format(ws=WSC, ident=IDENTIFIER)
# Closing pseudo group (`)`)
PAT_PSEUDO_CLOSE = r'{ws}*\)'.format(ws=WSC)
# Pseudo element (`::pseudo-element`)
PAT_PSEUDO_ELEMENT = r':{}'.format(PAT_PSEUDO_CLASS)
# At rule (`@page`, etc.) (not supported)
PAT_AT_RULE = r'@P{ident}'.format(ident=IDENTIFIER)
# Pseudo class `nth-child` (`:nth-child(an+b [of S]?)`, `:first-child`, etc.)
PAT_PSEUDO_NTH_CHILD = r'''
(?P<pseudo_nth_child>:nth-(?:last-)?child
\({ws}*(?P<nth_child>{nth}|even|odd))(?:{wsc}*\)|(?P<of>{comments}*{ws}{wsc}*of{comments}*{ws}{wsc}*))
'''.format(wsc=WSC, comments=COMMENTS, ws=WS, nth=NTH)
# Pseudo class `nth-of-type` (`:nth-of-type(an+b)`, `:first-of-type`, etc.)
PAT_PSEUDO_NTH_TYPE = r'''
(?P<pseudo_nth_type>:nth-(?:last-)?of-type
\({ws}*(?P<nth_type>{nth}|even|odd)){ws}*\)
'''.format(ws=WSC, nth=NTH)
# Pseudo class language (`:lang("*-de", en)`)
PAT_PSEUDO_LANG = r':lang\({ws}*(?P<lang>{value}(?:{ws}*,{ws}*{value})*){ws}*\)'.format(ws=WSC, value=VALUE)
# Pseudo class direction (`:dir(ltr)`)
PAT_PSEUDO_DIR = r':dir\({ws}*(?P<dir>ltr|rtl){ws}*\)'.format(ws=WSC)
# Combining characters (`>`, `~`, ` `, `+`, `,`)
PAT_COMBINE = r'{ws}*?(?P<relation>[,+>~]|[ \t\r\n\f](?![,+>~])){ws}*'.format(ws=WSC)
# Extra: Contains (`:contains(text)`)
PAT_PSEUDO_CONTAINS = r':contains\({ws}*(?P<value>{value}){ws}*\)'.format(ws=WSC, value=VALUE)

# Regular expressions
# CSS escape pattern
RE_CSS_ESC = re.compile(r'(?:(\\[a-f0-9]{{1,6}}{ws}?)|(\\[^\r\n\f]))'.format(ws=WSC), re.I)
# Pattern to break up `nth` specifiers
RE_NTH = re.compile(
    r'(?P<s1>[-+])?(?P<a>[0-9]+n?|n)(?:(?<=n){ws}*(?P<s2>[-+]){ws}*(?P<b>[0-9]+))?'.format(ws=WSC),
    re.I
)
# Pattern to iterate multiple languages.
RE_LANG = re.compile(r'(?:(?P<value>{value})|(?P<split>{ws}*,{ws}*))'.format(ws=WSC, value=VALUE), re.X)
# Whitespace checks
RE_WS = re.compile(WS)
RE_WS_BEGIN = re.compile('^{}*'.format(WSC))
RE_WS_END = re.compile('{}*$'.format(WSC))

# Constants
# List split token
SPLIT = ','
# Relation type `:has()` descendant, the default relation type.
REL_HAS_CHILD = ": "

# Parse flags
FLG_PSEUDO = 0x01
FLG_NOT = 0x02
FLG_RELATIVE = 0x04
FLG_DEFAULT = 0x08
FLG_HTML = 0x10
FLG_INDETERMINATE = 0x20
FLG_OPEN = 0x40

# Maximum cached patterns to store
_MAXCACHE = 500


@util.lru_cache(maxsize=_MAXCACHE)
def _cached_css_compile(pattern, namespaces, flags):
    """Cached CSS compile."""

    return cm.SoupSieve(
        pattern,
        CSSParser(pattern, flags).process_selectors(),
        namespaces,
        flags
    )


def _purge_cache():
    """Purge the cache."""

    _cached_css_compile.cache_clear()


def css_unescape(string):
    """Unescape CSS value."""

    def replace(m):
        """Replace with the appropriate substitute."""

        return util.uchr(int(m.group(1)[1:], 16)) if m.group(1) else m.group(2)[1:]

    return RE_CSS_ESC.sub(replace, string)


class SelectorPattern(object):
    """Selector pattern."""

    def __init__(self, pattern):
        """Initialize."""

        self.pattern = re.compile(pattern, re.I | re.X | re.U)

    def enabled(self, flags):
        """Enabled."""

        return True


class _Selector(object):
    """
    Intermediate selector class.

    This stores selector data for a compound selector as we are acquiring them.
    Once we are done collecting the data for a compound selector, we freeze
    the data in an object that can be pickled and hashed.
    """

    def __init__(self, **kwargs):
        """Initialize."""

        self.tag = kwargs.get('tag', None)
        self.ids = kwargs.get('ids', [])
        self.classes = kwargs.get('classes', [])
        self.attributes = kwargs.get('attributes', [])
        self.nth = kwargs.get('nth', [])
        self.selectors = kwargs.get('selectors', [])
        self.relations = kwargs.get('relations', [])
        self.rel_type = kwargs.get('rel_type', None)
        self.contains = kwargs.get('contains', [])
        self.lang = kwargs.get('lang', [])
        self.flags = kwargs.get('flags', 0)
        self.no_match = kwargs.get('no_match', False)

    def _freeze_relations(self, relations):
        """Freeze relation."""

        if relations:
            sel = relations[0]
            sel.relations.extend(relations[1:])
            return ct.SelectorList([sel.freeze()])
        else:
            return ct.SelectorList()

    def freeze(self):
        """Freeze self."""

        if self.no_match:
            return ct.NullSelector()
        else:
            return ct.Selector(
                self.tag,
                tuple(self.ids),
                tuple(self.classes),
                tuple(self.attributes),
                tuple(self.nth),
                tuple(self.selectors),
                self._freeze_relations(self.relations),
                self.rel_type,
                tuple(self.contains),
                tuple(self.lang),
                self.flags
            )

    def __str__(self):  # pragma: no cover
        """String representation."""

        return (
            '_Selector(tag={!r}, ids={!r}, classes={!r}, attributes={!r}, nth={!r}, selectors={!r}, '
            'relations={!r}, rel_type={!r}, contains={!r}, lang={!r}, flags={!r}, no_match={!r})'
        ).format(
            self.tag, self.ids, self.classes, self.attributes, self.nth, self.selectors,
            self.relations, self.rel_type, self.contains, self.lang, self.flags, self.no_match
        )

    __repr__ = __str__


class CSSParser(object):
    """Parse CSS selectors."""

    css_tokens = OrderedDict(
        [
            ("pseudo_close", SelectorPattern(PAT_PSEUDO_CLOSE)),
            ("pseudo_contains", SelectorPattern(PAT_PSEUDO_CONTAINS)),
            ("pseudo_nth_child", SelectorPattern(PAT_PSEUDO_NTH_CHILD)),
            ("pseudo_nth_type", SelectorPattern(PAT_PSEUDO_NTH_TYPE)),
            ("pseudo_lang", SelectorPattern(PAT_PSEUDO_LANG)),
            ("pseudo_dir", SelectorPattern(PAT_PSEUDO_DIR)),
            ("pseudo_class", SelectorPattern(PAT_PSEUDO_CLASS)),
            ("pseudo_element", SelectorPattern(PAT_PSEUDO_ELEMENT)),
            ("at_rule", SelectorPattern(PAT_AT_RULE)),
            ("id", SelectorPattern(PAT_ID)),
            ("class", SelectorPattern(PAT_CLASS)),
            ("tag", SelectorPattern(PAT_TAG)),
            ("attribute", SelectorPattern(PAT_ATTR)),
            ("combine", SelectorPattern(PAT_COMBINE))
        ]
    )

    def __init__(self, selector, flags=0):
        """Initialize."""

        self.pattern = selector
        self.flags = flags
        self.debug = self.flags & util.DEBUG

    def parse_attribute_selector(self, sel, m, has_selector):
        """Create attribute selector from the returned regex match."""

        op = m.group('cmp')
        if op and op.startswith('!'):
            # Equivalent to `:not([attr=value])`
            attr = m.group('ns_attr')
            value = m.group('value')
            case = m.group('case')
            if not case:
                case = ''
            sel.selectors.append(
                self.parse_selectors(
                    # Simulate the content of `:not`, but make the attribute as `=` instead of `!=`.
                    self.selector_iter('[{}={} {}]'.format(attr, value, case)),
                    m.end(0),
                    FLG_PSEUDO | FLG_NOT
                )
            )
            has_selector = True
        else:
            case = util.lower(m.group('case')) if m.group('case') else None
            parts = [css_unescape(a) for a in m.group('ns_attr').split('|')]
            ns = ''
            is_type = False
            pattern2 = None
            if len(parts) > 1:
                ns = parts[0]
                attr = parts[1]
            else:
                attr = parts[0]
            if case:
                flags = re.I if case == 'i' else 0
            elif util.lower(attr) == 'type':
                flags = re.I
                is_type = True
            else:
                flags = 0

            if op:
                value = css_unescape(
                    m.group('value')[1:-1] if m.group('value').startswith(('"', "'")) else m.group('value')
                )
            else:
                value = None
            if not op:
                # Attribute name
                pattern = None
            elif op.startswith('^'):
                # Value start with
                pattern = re.compile(r'^%s.*' % re.escape(value), flags)
            elif op.startswith('$'):
                # Value ends with
                pattern = re.compile(r'.*?%s$' % re.escape(value), flags)
            elif op.startswith('*'):
                # Value contains
                pattern = re.compile(r'.*?%s.*' % re.escape(value), flags)
            elif op.startswith('~'):
                # Value contains word within space separated list
                # `~=` should match nothing if it is empty or contains whitespace,
                # so if either of these cases is present, use `[^\s\S]` which cannot be matched.
                value = r'[^\s\S]' if not value or RE_WS.search(value) else re.escape(value)
                pattern = re.compile(r'.*?(?:(?<=^)|(?<= ))%s(?=(?:[ ]|$)).*' % value, flags)
            elif op.startswith('|'):
                # Value starts with word in dash separated list
                pattern = re.compile(r'^%s(?:-.*)?$' % re.escape(value), flags)
            else:
                # Value matches
                pattern = re.compile(r'^%s$' % re.escape(value), flags)
            if is_type and pattern:
                pattern2 = re.compile(pattern.pattern)
            has_selector = True
            sel.attributes.append(ct.SelectorAttribute(attr, ns, pattern, pattern2))
        return has_selector

    def parse_tag_pattern(self, sel, m, has_selector):
        """Parse tag pattern from regex match."""

        parts = [css_unescape(x) for x in m.group(0).split('|')]
        if len(parts) > 1:
            prefix = parts[0]
            tag = parts[1]
        else:
            tag = parts[0]
            prefix = None
        sel.tag = ct.SelectorTag(tag, prefix)
        has_selector = True
        return has_selector

    def parse_pseudo_class(self, sel, m, has_selector, iselector):
        """Parse pseudo class."""

        complex_pseudo = False
        pseudo = util.lower(m.group('name'))
        if m.group('open'):
            complex_pseudo = True
        if complex_pseudo and pseudo in PSEUDO_COMPLEX:
            has_selector = self.parse_pseudo_open(sel, pseudo, has_selector, iselector, m.end(0))
        elif not complex_pseudo and pseudo in PSEUDO_SIMPLE:
            if pseudo == ':root':
                sel.flags |= ct.SEL_ROOT
            elif pseudo == ':scope':
                sel.flags |= ct.SEL_SCOPE
            elif pseudo == ':empty':
                sel.flags |= ct.SEL_EMPTY
            elif pseudo in (':link', ':any-link'):
                sel.selectors.append(CSS_LINK)
            elif pseudo == ':checked':
                sel.selectors.append(CSS_CHECKED)
            elif pseudo == ':default':
                sel.selectors.append(CSS_DEFAULT)
            elif pseudo == ':indeterminate':
                sel.selectors.append(CSS_INDETERMINATE)
            elif pseudo == ":disabled":
                sel.selectors.append(CSS_DISABLED)
            elif pseudo == ":enabled":
                sel.selectors.append(CSS_ENABLED)
            elif pseudo == ":required":
                sel.selectors.append(CSS_REQUIRED)
            elif pseudo == ":optional":
                sel.selectors.append(CSS_OPTIONAL)
            elif pseudo == ":read-only":
                sel.selectors.append(CSS_READ_ONLY)
            elif pseudo == ":read-write":
                sel.selectors.append(CSS_READ_WRITE)
            elif pseudo == ":placeholder-shown":
                sel.selectors.append(CSS_PLACEHOLDER_SHOWN)
            elif pseudo == ':first-child':
                sel.nth.append(ct.SelectorNth(1, False, 0, False, False, ct.SelectorList()))
            elif pseudo == ':last-child':
                sel.nth.append(ct.SelectorNth(1, False, 0, False, True, ct.SelectorList()))
            elif pseudo == ':first-of-type':
                sel.nth.append(ct.SelectorNth(1, False, 0, True, False, ct.SelectorList()))
            elif pseudo == ':last-of-type':
                sel.nth.append(ct.SelectorNth(1, False, 0, True, True, ct.SelectorList()))
            elif pseudo == ':only-child':
                sel.nth.extend(
                    [
                        ct.SelectorNth(1, False, 0, False, False, ct.SelectorList()),
                        ct.SelectorNth(1, False, 0, False, True, ct.SelectorList())
                    ]
                )
            elif pseudo == ':only-of-type':
                sel.nth.extend(
                    [
                        ct.SelectorNth(1, False, 0, True, False, ct.SelectorList()),
                        ct.SelectorNth(1, False, 0, True, True, ct.SelectorList())
                    ]
                )
            has_selector = True
        elif complex_pseudo and pseudo in PSEUDO_COMPLEX_NO_MATCH:
            self.parse_selectors(iselector, m.end(0), FLG_PSEUDO | FLG_OPEN)
            sel.no_match = True
            has_selector = True
        elif not complex_pseudo and pseudo in PSEUDO_SIMPLE_NO_MATCH:
            sel.no_match = True
            has_selector = True
        elif pseudo in PSEUDO_SUPPORTED:
            raise SyntaxError("Invalid syntax for pseudo class '{}'".format(pseudo))
        else:
            raise NotImplementedError(
                "'{}' pseudo-class is not implemented at this time".format(pseudo)
            )

        return has_selector

    def parse_pseudo_nth(self, sel, m, has_selector, iselector):
        """Parse `nth` pseudo."""

        mdict = m.groupdict()
        postfix = '_child' if mdict.get('pseudo_nth_child') else '_type'
        content = mdict.get('nth' + postfix)
        if content == 'even':
            s1 = 2
            s2 = 2
            var = True
        elif content == 'odd':
            s1 = 2
            s2 = 1
            var = True
        else:
            nth_parts = RE_NTH.match(content)
            s1 = '-' if nth_parts.group('s1') and nth_parts.group('s1') == '-' else ''
            a = nth_parts.group('a')
            var = a.endswith('n')
            if a.startswith('n'):
                s1 += '1'
            elif var:
                s1 += a[:-1]
            else:
                s1 += a
            s2 = '-' if nth_parts.group('s2') and nth_parts.group('s2') == '-' else ''
            if nth_parts.group('b'):
                s2 += nth_parts.group('b')
            else:
                s2 = '0'
            s1 = int(s1, 16)
            s2 = int(s2, 16)

        pseudo_sel = util.lower(m.group('pseudo_nth' + postfix))
        if postfix == '_child':
            if m.group('of'):
                # Parse the rest of `of S`.
                nth_sel = self.parse_selectors(iselector, m.end(0), FLG_PSEUDO | FLG_OPEN)
            else:
                # Use default `*|*` for `of S`.
                nth_sel = CSS_NTH_OF_S_DEFAULT
            if pseudo_sel.startswith(':nth-child'):
                sel.nth.append(ct.SelectorNth(s1, var, s2, False, False, nth_sel))
            elif pseudo_sel.startswith(':nth-last-child'):
                sel.nth.append(ct.SelectorNth(s1, var, s2, False, True, nth_sel))
        else:
            if pseudo_sel.startswith(':nth-of-type'):
                sel.nth.append(ct.SelectorNth(s1, var, s2, True, False, ct.SelectorList()))
            elif pseudo_sel.startswith(':nth-last-of-type'):
                sel.nth.append(ct.SelectorNth(s1, var, s2, True, True, ct.SelectorList()))
        has_selector = True
        return has_selector

    def parse_pseudo_open(self, sel, name, has_selector, iselector, index):
        """Parse pseudo with opening bracket."""

        flags = FLG_PSEUDO | FLG_OPEN
        if name == ':not':
            flags |= FLG_NOT
        if name == ':has':
            flags |= FLG_RELATIVE

        sel.selectors.append(self.parse_selectors(iselector, index, flags))
        has_selector = True
        return has_selector

    def parse_has_split(self, sel, m, has_selector, selectors, rel_type):
        """Parse splitting tokens."""

        if m.group('relation') == SPLIT:
            if not has_selector:
                raise SyntaxError("Cannot start or end selector with '{}'".format(m.group('relation')))
            sel.rel_type = rel_type
            selectors[-1].relations.append(sel)
            rel_type = REL_HAS_CHILD
            selectors.append(_Selector())
        else:
            if has_selector:
                sel.rel_type = rel_type
                selectors[-1].relations.append(sel)
            rel_type = ':' + m.group('relation')
        sel = _Selector()

        has_selector = False
        return has_selector, sel, rel_type

    def parse_split(self, sel, m, has_selector, selectors, relations, is_pseudo):
        """Parse splitting tokens."""

        if not has_selector:
            raise SyntaxError("Cannot start or end selector with '{}'".format(m.group('relation')))
        if m.group('relation') == SPLIT:
            if not sel.tag and not is_pseudo:
                # Implied `*`
                sel.tag = ct.SelectorTag('*', None)
            sel.relations.extend(relations)
            selectors.append(sel)
            del relations[:]
        else:
            sel.relations.extend(relations)
            rel_type = m.group('relation').strip()
            if not rel_type:
                rel_type = ' '
            sel.rel_type = rel_type
            del relations[:]
            relations.append(sel)
        sel = _Selector()

        has_selector = False
        return has_selector, sel

    def parse_class_id(self, sel, m, has_selector):
        """Parse HTML classes and ids."""

        selector = m.group(0)
        if selector.startswith('.'):
            sel.classes.append(css_unescape(selector[1:]))
            has_selector = True
        else:
            sel.ids.append(css_unescape(selector[1:]))
            has_selector = True
        return has_selector

    def parse_pseudo_contains(self, sel, m, has_selector):
        """Parse contains."""

        content = m.group('value')
        if content.startswith(("'", '"')):
            content = content[1:-1]
        content = css_unescape(content)
        sel.contains.append(content)
        has_selector = True
        return has_selector

    def parse_pseudo_lang(self, sel, m, has_selector):
        """Parse pseudo language."""

        lang = m.group('lang')
        patterns = []
        for token in RE_LANG.finditer(lang):
            if token.group('split'):
                continue
            value = token.group('value')
            if value.startswith(('"', "'")):
                value = value[1:-1]
            parts = css_unescape(value).split('-')

            new_parts = []
            first = True
            for part in parts:
                if part == '*' and first:
                    new_parts.append('(?!x\b)[a-z0-9]+?')
                elif part != '*':
                    new_parts.append(('' if first else '(-(?!x\b)[a-z0-9]+)*?\\-') + re.escape(part))
                if first:
                    first = False
            patterns.append(re.compile(r'^{}(?:-.*)?$'.format(''.join(new_parts)), re.I))
        sel.lang.append(ct.SelectorLang(patterns))
        has_selector = True

        return has_selector

    def parse_pseudo_dir(self, sel, m, has_selector):
        """Parse pseudo direction."""

        value = ct.SEL_DIR_LTR if util.lower(m.group('dir')) == 'ltr' else ct.SEL_DIR_RTL
        sel.flags |= value
        has_selector = True
        return has_selector

    def parse_selectors(self, iselector, index=0, flags=0):
        """Parse selectors."""

        sel = _Selector()
        selectors = []
        has_selector = False
        closed = False
        relations = []
        rel_type = REL_HAS_CHILD
        split_last = False
        is_open = flags & FLG_OPEN
        is_pseudo = flags & FLG_PSEUDO
        is_relative = flags & FLG_RELATIVE
        is_not = flags & FLG_NOT
        is_html = flags & FLG_HTML
        is_default = flags & FLG_DEFAULT
        is_indeterminate = flags & FLG_INDETERMINATE

        if self.debug:  # pragma: no cover
            if is_pseudo:
                print('    is_pseudo: True')
            if is_open:
                print('    is_open: True')
            if is_relative:
                print('    is_relative: True')
            if is_not:
                print('    is_not: True')
            if is_html:
                print('    is_html: True')
            if is_default:
                print('    is_default: True')
            if is_indeterminate:
                print('    is_indeterminate: True')

        if is_relative:
            selectors.append(_Selector())

        try:
            while True:
                key, m = next(iselector)

                # Handle parts
                if key == "at_rule":
                    raise NotImplementedError("At-rules found at position {}".format(m.start(0)))
                elif key == 'pseudo_class':
                    has_selector = self.parse_pseudo_class(sel, m, has_selector, iselector)
                elif key == 'pseudo_element':
                    raise NotImplementedError("Psuedo-element found at position {}".format(m.start(0)))
                elif key == 'pseudo_contains':
                    has_selector = self.parse_pseudo_contains(sel, m, has_selector)
                elif key in ('pseudo_nth_type', 'pseudo_nth_child'):
                    has_selector = self.parse_pseudo_nth(sel, m, has_selector, iselector)
                elif key == 'pseudo_lang':
                    has_selector = self.parse_pseudo_lang(sel, m, has_selector)
                elif key == 'pseudo_dir':
                    has_selector = self.parse_pseudo_dir(sel, m, has_selector)
                    # Currently only supports HTML
                    is_html = True
                elif key == 'pseudo_close':
                    if split_last:
                        raise SyntaxError("Expecting more selectors at postion {}".format(m.start(0)))
                    if is_open:
                        closed = True
                        break
                    else:
                        raise SyntaxError("Unmatched pseudo-class close at postion {}".format(m.start(0)))
                elif key == 'combine':
                    if split_last:
                        raise SyntaxError("Unexpected combining character at position {}".format(m.start(0)))
                    if is_relative:
                        has_selector, sel, rel_type = self.parse_has_split(
                            sel, m, has_selector, selectors, rel_type
                        )
                    else:
                        has_selector, sel = self.parse_split(sel, m, has_selector, selectors, relations, is_pseudo)
                    split_last = True
                    continue
                elif key == 'attribute':
                    has_selector = self.parse_attribute_selector(sel, m, has_selector)
                elif key == 'tag':
                    if has_selector:
                        raise SyntaxError("Tag name found at position {} instead of at the start".format(m.start(0)))
                    has_selector = self.parse_tag_pattern(sel, m, has_selector)
                elif key in ('class', 'id'):
                    has_selector = self.parse_class_id(sel, m, has_selector)
                split_last = False

                index = m.end(0)
        except StopIteration:
            pass

        if is_open and not closed:
            raise SyntaxError("Unclosed pseudo-class at position {}".format(index))

        if split_last:
            raise SyntaxError("Expected more selectors at position {}".format(index))

        if has_selector:
            if not sel.tag and not is_pseudo:
                # Implied `*`
                sel.tag = ct.SelectorTag('*', None)
            if is_relative:
                sel.rel_type = rel_type
                selectors[-1].relations.append(sel)
            else:
                sel.relations.extend(relations)
                del relations[:]
                selectors.append(sel)
        elif is_relative:
            # We will always need to finish a selector when `:has()` is used as it leads with combining.
            raise SyntaxError('Missing selectors after combining type.')

        # For default, the last patter in the list will be one that requires additional
        # logic, flag that selector as "default" so the required logic will be executed
        # along with the pattern.
        if is_default:
            selectors[-1].flags = ct.SEL_DEFAULT
        if is_indeterminate:
            selectors[-1].flags = ct.SEL_INDETERMINATE

        return ct.SelectorList([s.freeze() for s in selectors], is_not, is_html)

    def selector_iter(self, pattern):
        """Iterate selector tokens."""

        # Ignore whitespace and comments at start and end of pattern
        m = RE_WS_BEGIN.search(pattern)
        index = m.end(0) if m else 0
        m = RE_WS_END.search(pattern)
        end = (m.start(0) - 1) if m else (len(pattern) - 1)

        if self.debug:  # pragma: no cover
            print('## PARSING: {!r}'.format(pattern))
        while index <= end:
            m = None
            for k, v in self.css_tokens.items():
                if not v.enabled(self.flags):  # pragma: no cover
                    continue
                m = v.pattern.match(pattern, index)
                if m:
                    if self.debug:  # pragma: no cover
                        print("TOKEN: '{}' --> {!r} at position {}".format(k, m.group(0), m.start(0)))
                    index = m.end(0)
                    yield k, m
                    break
            if m is None:
                if self.debug:  # pragma: no cover
                    print("TOKEN: 'invalid' --> {!r} at position {}".format(pattern[index], index))
                raise SyntaxError("Invlaid character {!r} at position {}".format(pattern[index], index))
        if self.debug:  # pragma: no cover
            print('## END PARSING')

    def process_selectors(self, index=0, flags=0):
        """
        Process selectors.

        We do our own selectors as BeautifulSoup4 has some annoying quirks,
        and we don't really need to do nth selectors or siblings or
        descendants etc.
        """

        return self.parse_selectors(self.selector_iter(self.pattern), index, flags)


# Precompile CSS selector lists for pseudo-classes (additional logic may be required beyond the pattern)
# A few patterns are order dependent as they use patterns previous compiled.

# CSS pattern for `:link` and `:any-link`
CSS_LINK = CSSParser(
    ':is(a, area, link)[href]'
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
# CSS pattern for `:checked`
CSS_CHECKED = CSSParser(
    '''
    :is(input[type=checkbox], input[type=radio])[checked],
    select > option[selected]
    '''
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
# CSS pattern for `:default` (must compile CSS_CHECKED first)
CSS_DEFAULT = CSSParser(
    '''
    :checked,

    /*
    This pattern must be at the end.
    Special logic is applied to the last selector.
    */
    form :is(button, input)[type="submit"]
    '''
).process_selectors(flags=FLG_PSEUDO | FLG_HTML | FLG_DEFAULT)
# CSS pattern for `:indeterminate`
CSS_INDETERMINATE = CSSParser(
    '''
    input[type="checkbox"][indeterminate],
    input[type="radio"]:is(:not([name]), [name=""]):not([checked]),
    progress:not([value]),

    /*
    This pattern must be at the end.
    Special logic is applied to the last selector.
    */
    input[type="radio"][name][name!='']:not([checked])
    '''
).process_selectors(flags=FLG_PSEUDO | FLG_HTML | FLG_INDETERMINATE)
# CSS pattern for `:disabled`
CSS_DISABLED = CSSParser(
    '''
    :is(input[type!=hidden], button, select, textarea, fieldset, optgroup, option)[disabled],
    optgroup[disabled] > option,
    fieldset[disabled] > :not(legend) :is(input[type!=hidden], button, select, textarea),
    fieldset[disabled] > :is(input[type!=hidden], button, select, textarea)
    '''
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
# CSS pattern for `:enabled`
CSS_ENABLED = CSSParser(
    '''
    :is(a, area, link)[href],
    :is(fieldset, optgroup):not([disabled]),
    option:not(optgroup[disabled] *):not([disabled]),
    :is(input[type!=hidden], button, select, textarea):not(
        fieldset[disabled] > :not(legend) *,
        fieldset[disabled] > *
    ):not([disabled])
    '''
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
# CSS pattern for `:required`
CSS_REQUIRED = CSSParser(
    ':is(input, textarea, select)[required]'
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
# CSS pattern for `:optional`
CSS_OPTIONAL = CSSParser(
    ':is(input, textarea, select):not([required])'
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
# CSS pattern for `:placeholder-shown`
CSS_PLACEHOLDER_SHOWN = CSSParser(
    '''
    :is(
        input:is(
            :not([type]),
            [type=""],
            [type=text],
            [type=search],
            [type=url],
            [type=tel],
            [type=email],
            [type=password],
            [type=number]
        ),
        textarea
    )[placeholder][placeholder!='']
    '''
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
# CSS pattern default for `:nth-child` "of S" feature
CSS_NTH_OF_S_DEFAULT = CSSParser(
    '*|*'
).process_selectors(flags=FLG_PSEUDO)
# CSS pattern for `:read-write` (CSS_DISABLED must be compiled first)
CSS_READ_WRITE = CSSParser(
    '''
    :is(
        textarea,
        input:is(
            :not([type]),
            [type=""],
            [type=text],
            [type=search],
            [type=url],
            [type=tel],
            [type=email],
            [type=number],
            [type=password],
            [type=date],
            [type=datetime-local],
            [type=month],
            [type=time],
            [type=week]
        )
    ):not([readonly], :disabled),
    :is([contenteditable=""], [contenteditable="true" i])
    '''
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
# CSS pattern for `:read-only`
CSS_READ_ONLY = CSSParser(
    '''
    :not(:read-write)
    '''
).process_selectors(flags=FLG_PSEUDO | FLG_HTML)
