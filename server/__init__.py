#!/usr/bin/env python
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
from girder.models.model_base import ModelImporter
from girder.constants import AccessType

from .rest_slicer_cli import genRESTEndPointsForSlicerCLIsInDockerCache
from .docker_resource import DockerResource


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


def load(info):
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
    events.bind('data.process', info['name'], _onUpload)
