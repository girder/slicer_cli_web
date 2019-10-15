# -*- coding: utf-8 -*-

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

import json

from girder import events
from girder.utility.model_importer import ModelImporter
from girder.plugin import getPlugin, GirderPlugin
from girder.constants import AccessType
from girder_worker import GirderWorkerPluginABC
from girder_worker import GirderWorkerPluginABC
from pkg_resources import DistributionNotFound, get_distribution

from .rest_slicer_cli import genRESTEndPointsForSlicerCLIsInDockerCache
from .docker_resource import DockerResource
from .models import DockerImageModel


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


__license__ = 'Apache 2.0'


def _onUpload(event):
    try:
        ref = json.loads(event.info.get('reference'))
    except (ValueError, TypeError):
        return

    if isinstance(ref, dict) and ref.get('type') == 'slicer_cli.parameteroutput':
        jobModel = ModelImporter.model('job', 'jobs')
        job = jobModel.load(ref['jobId'], force=True, exc=True)

        file = event.info['file']

        # Add link to job model to the output item
        jobModel.updateJob(job, otherFields={
            'slicerCLIBindings.outputs.parameters': file['_id']
        })


class SlicerCLIWebPlugin(GirderPlugin):
    DISPLAY_NAME = 'Slicer CLI Web'         # a user-facing plugin name, the plugin is still
                                            # referenced internally by the entrypoint name.
    CLIENT_SOURCE_PATH = 'web_client'       # path to the web client relative to the python package

    def load(self, info):
        getPlugin('jobs').load(info)  # load plugins you depend on
        getPlugin('worker').load(info)  # load plugins you depend on

        ModelImporter.registerModel('docker_image_model', DockerImageModel, 'slicer_cli_web')

        # passed in resource name must match the attribute added to info[apiroot]
        resource = DockerResource('slicer_cli_web')
        info['apiRoot'].slicer_cli_web = resource

        dockerImageModel = ModelImporter.model('docker_image_model',
                                            'slicer_cli_web')
        dockerCache = dockerImageModel.loadAllImages()

        genRESTEndPointsForSlicerCLIsInDockerCache(resource, dockerCache)

        ModelImporter.model('job', 'jobs').exposeFields(level=AccessType.READ, fields={
            'slicerCLIBindings'})

        events.bind('jobs.job.update.after', resource.resourceName,
                    resource.AddRestEndpoints)
        events.bind('data.process', 'slicer_cli_web', _onUpload)


class SlicerCLIWebWorkerPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return ['slicer_cli_web.direct_docker_run']
