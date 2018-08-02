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

from tests import base


# boiler plate to start and stop the server if needed
def setUpModule():
    base.enabledPlugins.append('slicer_cli_web')
    base.startServer()


def tearDownModule():
    base.stopServer()


# Test import of slicer_cli_web
class ImportPackageTest(base.TestCase):

    def test_slicer_cli_web(self):
        from girder.plugins import slicer_cli_web  # noqa

    def test_rest_slicer_cli(self):
        from girder.plugins.slicer_cli_web import rest_slicer_cli  # noqa

    def test_docker_image_model(self):
        from girder.models.model_base import ModelImporter

        raised = False
        try:
            ModelImporter.model('docker_image_model', 'slicer_cli_web')  # noqa
        except Exception as e:
            raised = True
            print(str(e))

        self.assertFalse(raised, 'docker_image_model import failed')

    def test_docker_resource(self):
        from girder.plugins.slicer_cli_web import docker_resource  # noqa

    def test_cli_list_entrypoint(self):
        from girder.plugins.slicer_cli_web import cli_list_entrypoint  # noqa
