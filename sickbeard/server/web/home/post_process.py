# coding=utf-8

from __future__ import unicode_literals

from tornado.routes import route
from sickbeard import processTV
from sickrage.helper.encoding import ss
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.home.handler import Home


@route('/home/postprocess(/?.*)')
class HomePostProcess(Home):
    def __init__(self, *args, **kwargs):
        super(HomePostProcess, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='home_postprocess.mako')
        return t.render(title='Post Processing', header='Post Processing', topmenu='home', controller='home', action='postProcess')

    # TODO: PR to NZBtoMedia so that we can rename dir to proc_dir, and type to proc_type.
    # Using names of builtins as var names is bad
    # pylint: disable=redefined-builtin
    def processEpisode(self, proc_dir=None, nzbName=None, jobName=None, quiet=None, process_method=None, force=None,
                       is_priority=None, delete_on='0', failed='0', type='auto', *args, **kwargs):
        nzb_name = nzbName

        def argToBool(argument):
            if isinstance(argument, basestring):
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
            nzb_name = ss(nzb_name) if nzb_name else nzb_name

            result = processTV.processDir(
                ss(proc_dir), nzb_name, process_method=process_method, force=argToBool(force),
                is_priority=argToBool(is_priority), delete_on=argToBool(delete_on), failed=argToBool(failed), proc_type=type
            )

            if quiet is not None and int(quiet) == 1:
                return result

            result = result.replace('\n', '<br>\n')
            return self._genericMessage('Postprocessing results', result)
