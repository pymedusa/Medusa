#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import unicode_literals

import inspect

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles

from stevedore import extension


def _get_docstring(plugin):
    return inspect.getdoc(plugin) or ''


def _simple_list(mgr):
    for name in sorted(mgr.names()):
        ext = mgr[name]
        doc = _get_docstring(ext.plugin) or '\n'
        summary = doc.splitlines()[0].strip()
        yield('* {0!s} -- {1!s}'.format(ext.name, summary),
              ext.entry_point.module_name)


def _detailed_list(mgr, over='', under='-', titlecase=False):
    for name in sorted(mgr.names()):
        ext = mgr[name]
        if over:
            yield (over * len(ext.name), ext.entry_point.module_name)
        if titlecase:
            yield (ext.name.title(), ext.entry_point.module_name)
        else:
            yield (ext.name, ext.entry_point.module_name)
        if under:
            yield (under * len(ext.name), ext.entry_point.module_name)
        yield ('\n', ext.entry_point.module_name)
        doc = _get_docstring(ext.plugin)
        if doc:
            yield (doc, ext.entry_point.module_name)
        else:
            yield ('.. warning:: No documentation found in {0!s}'.format(ext.entry_point),
                   ext.entry_point.module_name)
        yield ('\n', ext.entry_point.module_name)


class ListPluginsDirective(rst.Directive):
    """Present a simple list of the plugins in a namespace."""

    option_spec = {
        'class': directives.class_option,
        'detailed': directives.flag,
        'titlecase': directives.flag,
        'overline-style': directives.single_char_or_unicode,
        'underline-style': directives.single_char_or_unicode,
    }

    has_content = True

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        namespace = ' '.join(self.content).strip()
        app.info('documenting plugins from {0!r}'.format(namespace))
        overline_style = self.options.get('overline-style', '')
        underline_style = self.options.get('underline-style', '=')

        def report_load_failure(mgr, ep, err):
            app.warn(u'Failed to load {0!s}: {1!s}'.format(ep.module_name, err))

        mgr = extension.ExtensionManager(
            namespace,
            on_load_failure_callback=report_load_failure,
        )

        result = ViewList()

        titlecase = 'titlecase' in self.options

        if 'detailed' in self.options:
            data = _detailed_list(
                mgr, over=overline_style, under=underline_style,
                titlecase=titlecase)
        else:
            data = _simple_list(mgr)
        for text, source in data:
            for line in text.splitlines():
                result.append(line, source)

        # Parse what we have into a new section.
        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)

        return node.children


def setup(app):
    app.info('loading stevedore.sphinxext')
    app.add_directive('list-plugins', ListPluginsDirective)
