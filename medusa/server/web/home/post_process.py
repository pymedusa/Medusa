# coding=utf-8

from __future__ import unicode_literals

import json
import logging

from medusa import app
from medusa.logger.adapters.style import CustomBraceAdapter
from medusa.process_tv import PostProcessQueueItem
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home

from six import string_types, text_type

from tornroutes import route


log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


@route('/home/postprocess(/?.*)')
class HomePostProcess(Home):

    def __init__(self, *args, **kwargs):
        super(HomePostProcess, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the manual Post-Process page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()

    # TODO: move to apiv2
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
            return json.dumps({
                'status': 'failed',
                'message': 'Missing Post-Processing dir'
            })
        else:
            proc_dir = _decode(proc_dir)
            resource_name = _decode(nzbName)

            log.info('Post processing called with:\npath: {path}\nresource: {resource}', {
                'path': proc_dir, 'resource': resource_name
            })

            # Might look strange to explicitly check both. But, it's so I have a third option.
            # And that is that neither of both is passed. For example when called by legacy third parties.
            # Like nzbToMedia.
            run_async = argToBool(kwargs.pop('run_async', '0'))
            run_sync = argToBool(kwargs.pop('run_sync', '0'))

            if run_async:
                queue_item = PostProcessQueueItem(
                    path=proc_dir,
                    process_method=process_method,
                    info_hash=None,
                    resource_name=resource_name,
                    force=argToBool(force),
                    is_priority=argToBool(is_priority),
                    delete_on=argToBool(delete_on),
                    failed=argToBool(failed),
                    proc_type=proc_type,
                    ignore_subs=argToBool(ignore_subs)
                )
                app.post_processor_queue_scheduler.action.add_item(queue_item)

                return json.dumps({
                    'status': 'success',
                    'message': 'Post process action queued',
                    'queueItem': queue_item.to_json
                })

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

            if run_sync:
                return json.dumps({
                    'status': 'success',
                    'message': result.replace('\n', '<br>\n'),
                    'output': result.split('\n')
                })

            result = result.replace('\n', '<br>\n')
            return self._genericMessage('Post-processing results', result)
