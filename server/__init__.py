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


from girder import events


from .rest_slicer_cli import genRESTEndPointsForSlicerCLIsInDockerCache


from .docker_resource import DockerResource

from girder.models.model_base import ModelImporter


def load(info):

    # passed in resource name must match the attribute added to info[apiroot]
    resource = DockerResource('slicer_cli')
    info['apiRoot'].slicer_cli = resource

    dockerImageModel = ModelImporter.model('docker_image_model', 'slicer_cli')
    dockerCache = dockerImageModel.loadAllImages()

    genRESTEndPointsForSlicerCLIsInDockerCache(resource, dockerCache)

    events.bind('model.job.save.after', resource.resourceName,
                resource.AddRestEndpoints)
