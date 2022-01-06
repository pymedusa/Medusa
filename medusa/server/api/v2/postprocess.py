# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

import logging

from medusa import app
from medusa.logger.adapters.style import CustomBraceAdapter
from medusa.process_tv import PostProcessQueueItem
from medusa.server.api.v2.base import BaseRequestHandler

from tornado.escape import json_decode


log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


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
        process_method = data.get('process_method', app.PROCESS_METHOD)
        force = bool(data.get('force', False))
        is_priority = bool(data.get('is_priority', False))
        delete_on = bool(data.get('delete_on', False))
        failed = bool(data.get('failed', False))
        proc_type = data.get('proc_type', '')
        ignore_subs = bool(data.get('is_priority', False))

        if not proc_dir:
            if app.PROCESS_AUTOMATICALLY and app.TV_DOWNLOAD_DIR:
                proc_dir = app.TV_DOWNLOAD_DIR
                log.info('')
            return self._bad_request(
                'Missing attribute `proc_dir`. '
                'Provide a proc_dir. Or configure Scheduled postprocessing icw. a Post processing directory.'
            )

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
            ignore_subs=ignore_subs,
            process_single_resource=True
        )
        app.post_processor_queue_scheduler.action.add_item(queue_item)

        return self._created(data={
            'status': 'success',
            'message': 'Post process action queued',
            'queueItem': queue_item.to_json
        })
