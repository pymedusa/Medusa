# coding=utf-8

from __future__ import unicode_literals

from medusa import process_tv
from medusa.helper.encoding import ss
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home

from six import string_types

from tornroutes import route


@route('/home/postprocess(/?.*)')
class HomePostProcess(Home):

    def __init__(self, *args, **kwargs):
        super(HomePostProcess, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='home_postprocess.mako')
        return t.render(controller='home', action='postProcess')

    def processEpisode(self, proc_dir=None, nzbName=None, jobName=None, quiet=None, process_method=None, force=None,
                       is_priority=None, delete_on='0', failed='0', proc_type='auto', ignore_subs=None, *args, **kwargs):

        def argToBool(argument):
            if isinstance(argument, string_types):
                _arg = argument.strip().lower()
            else:
                _arg = argument

            if _arg in ['1', 'on', 'true', True]:
                return True
            elif _arg in ['0', 'off', 'false', False]:
                return False

            return argument

        if not proc_dir:
            return self.redirect('/home/postprocess/')
        else:
            resource_name = ss(nzbName) if nzbName else None

            result = process_tv.ProcessResult(ss(proc_dir), process_method=process_method).process(
                resource_name=resource_name, force=argToBool(force), is_priority=argToBool(is_priority),
                delete_on=argToBool(delete_on), failed=argToBool(failed), proc_type=type,
                ignore_subs=argToBool(ignore_subs)
            )

            if quiet is not None and int(quiet) == 1:
                return result

            result = result.replace('\n', '<br>\n')
            return self._genericMessage('Postprocessing results', result)
