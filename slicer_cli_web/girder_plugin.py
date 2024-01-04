###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import datetime
import json

from girder import events, logger
from girder.constants import AccessType
from girder.plugin import GirderPlugin, getPlugin
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from . import worker_tools
from .docker_resource import DockerResource
from .models import DockerImageItem


def _onUpload(event):
    try:
        ref = json.loads(event.info.get('reference'))
    except (ValueError, TypeError):
        return

    if isinstance(ref, dict) and ref.get('type') == 'slicer_cli.parameteroutput':
        job = Job().load(ref['jobId'], force=True, exc=True)

        file = event.info['file']

        # Add link to job model to the output item
        Job().updateJob(job, otherFields={
            'slicerCLIBindings.outputs.parameters': file['_id']
        })


class SlicerCLIWebPlugin(GirderPlugin):
    DISPLAY_NAME = 'Slicer CLI Web'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        try:
            getPlugin('worker').load(info)
        except Exception:
            logger.info('Girder working is unavailable')

        DockerImageItem.prepare()

        # resource name must match the attribute added to info[apiroot]
        resource = DockerResource('slicer_cli_web')
        info['apiRoot'].slicer_cli_web = resource

        Job().exposeFields(level=AccessType.READ, fields={'slicerCLIBindings'})

        events.bind('jobs.job.update.after', resource.resourceName,
                    resource.addRestEndpoints)
        events.bind('data.process', 'slicer_cli_web', _onUpload)

        count = 0
        for job in Job().find({
            'status': {'$in': [
                JobStatus.INACTIVE, JobStatus.QUEUED, JobStatus.RUNNING,
                # from girder_worker, but we don't strictly require its
                # existence
                820, 821, 822, 823, 824,
            ]},
            'updated': {'$lt': datetime.datetime.utcnow() - datetime.timedelta(days=7)}
        }, force=True):
            try:
                Job().updateJob(job, log='Canceled stale job.', status=JobStatus.CANCELED)
                count += 1
            except Exception:
                pass
        if count:
            logger.info('Marking %d old job(s) as cancelled' % count)
        worker_tools.start()
