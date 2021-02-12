# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

from medusa import app
from medusa.process_tv import PostProcessQueueItem
from medusa.server.api.v2.base import BaseRequestHandler

from tornado.escape import json_decode


class PostProcessHandler(BaseRequestHandler):
    """Postprocess request handler."""

    #: resource name
    name = 'postprocess'
    #: identifier
    identifier = ('identifier', r'[0-9a-f-]+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST',)

    def get(self, identifier):
        """Collect postprocess queue items.

        :param identifier:
        """
        queue_history = app.post_processor_queue_scheduler.action.history
        queue_history = [item for item in queue_history if item.name == 'POSTPROCESSQUEUE-POST-PROCESS']
        if identifier:
            queue_history = [item for item in queue_history if item.identifier == identifier]

        if len(queue_history) == 1:
            return self._ok(data=queue_history[0].to_json)
        return self._ok(data=[item.to_json for item in queue_history])

    def post(self, identifier=None):
        """Queue a postprocess job."""
        data = json_decode(self.request.body)

        proc_dir = data.get('proc_dir', '')
        resource = data.get('resource', '')
        process_method = data.get('process_method', False)
        force = data.get('force', False)
        is_priority = data.get('is_priority', False)
        delete_on = data.get('delete_on', False)
        failed = data.get('failed', False)
        proc_type = data.get('proc_type', False)
        ignore_subs = data.get('is_priority', False)

        if not proc_dir:
            return self._bad_request('Missing proc_dir')

        queue_item = PostProcessQueueItem(
            path=proc_dir,
            process_method=process_method,
            info_hash=None,
            resource_name=resource,
            force=force,
            is_priority=is_priority,
            delete_on=delete_on,
            failed=failed,
            proc_type=proc_type,
            ignore_subs=ignore_subs
        )
        app.post_processor_queue_scheduler.action.add_item(queue_item)

        return self._created(data={
            'status': 'success',
            'message': 'Post process action queued',
            'queueItem': queue_item.to_json
        })
