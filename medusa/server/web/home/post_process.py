# coding=utf-8

from __future__ import unicode_literals

from medusa import app
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home

from six import string_types, text_type

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

        def _decode(value):
            if not value or isinstance(value, text_type):
                return value

            return text_type(value, 'utf-8')

        if not proc_dir:
            return self.redirect('/home/postprocess/')
        else:
            proc_dir = _decode(proc_dir)
            resource_name = _decode(nzbName)

            result = app.post_processor_scheduler.action.run(
                path=proc_dir,
                process_method=process_method,
                resource_name=resource_name,
                force=argToBool(force),
                is_priority=argToBool(is_priority),
                delete_on=argToBool(delete_on),
                failed=argToBool(failed),
                proc_type=proc_type,
                ignore_subs=argToBool(ignore_subs)
            )

            if quiet is not None and int(quiet) == 1:
                return result

            result = result.replace('\n', '<br>\n')
            return self._genericMessage('Post-processing results', result)
