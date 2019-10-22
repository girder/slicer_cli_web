#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from tests import base


# boiler plate to start and stop the server if needed
def setUpModule():
    base.enabledPlugins.append('slicer_cli_web')
    base.startServer()


def tearDownModule():
    base.stopServer()


class RestSlicerCLITest(base.TestCase):
    def setUp(self):
        import datetime

        from girder.api import rest
        import girder_worker
        from girder_worker import utils as worker_utils
        from girder.models.file import File
        from girder.models.folder import Folder
        from girder.models.item import Item
        from girder.models.user import User

        base.TestCase.setUp(self)

        self.admin = User().createUser('admin', 'passwd', 'admin', 'admin', 'a@d.min')
        self.folder = Folder().createFolder(self.admin, 'folder', parentType='user')
        self.item = Item().createItem('item', self.admin, self.folder)
        self.file = File().createFile(self.admin, self.item, 'file', 7, self.assetstore)

        # Mock several functions so we can fake creating jobs
        def getCurrentToken():
            return {
                '_id': str(self.admin['_id']),
                'expires': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }

        def getWorkerApiUrl():
            return '/api/v1'

        self._origRestGetCurrentToken = rest.getCurrentToken
        self._origRestGetApiUrl = rest.getApiUrl
        self._origWorkerGetWorkerApiUrl = girder_worker.getWorkerApiUrl

        rest.getCurrentToken = getCurrentToken
        rest.getApiUrl = lambda x: '/api/v1'
        rest.setCurrentUser(self.admin)
        girder_worker.getWorkerApiUrl = worker_utils.getWorkerApiUrl = getWorkerApiUrl

    def tearDown(self):
        from girder.api import rest
        import girder_worker
        from girder_worker import utils as worker_utils

        rest.getCurrentToken = self._origRestGetCurrentToken
        rest.getApiUrl = self._origRestGetApiUrl
        girder_worker.getWorkerApiUrl = worker_utils.getWorkerApiUrl = self._origWorkerGetWorkerApiUrl
        base.TestCase.tearDown(self)

    def test_genHandlerToRunDockerCLI(self):
        from slicer_cli_web import docker_resource
        from slicer_cli_web import rest_slicer_cli
        from slicer_cli_web.models import CLIItem
        from girder.models.item import Item

        xmlpath = os.path.join(os.path.dirname(__file__), 'data', 'ExampleSpec.xml')

        girderCLIItem = Item().createItem('data', self.admin, self.folder)
        Item().setMetadata(girderCLIItem, dict(slicerCLIType='task', type='python', xml=open(xmlpath, 'rb').read()))

        resource = docker_resource.DockerResource('test')
        item = CLIItem(girderCLIItem)
        handlerFunc = rest_slicer_cli.genHandlerToRunDockerCLI(
            'dockerImage', CLIItem(item), resource)
        self.assertIsNotNone(handlerFunc)

        job = handlerFunc(params={
            'inputImageFile': str(self.file['_id']),
            'secondImageFile': str(self.file['_id']),
            'outputStainImageFile_1_folder': str(self.folder['_id']),
            'outputStainImageFile_1': 'sample1.png',
            'outputStainImageFile_2_folder': str(self.folder['_id']),
            'outputStainImageFile_2_name': 'sample2.png',
            'stainColor_1': '[0.5, 0.5, 0.5]',
            'stainColor_2': '[0.2, 0.3, 0.4]',
            'returnparameterfile_folder': str(self.folder['_id']),
            'returnparameterfile': 'output.data',
        })

        self.assertHasKeys(
            job['kwargs'],
            ['container_args', 'image', 'pull_image'])

        self.assertEqual(job['kwargs']['image'], 'dockerImage')
        self.assertEqual(job['kwargs']['pull_image'], False)
        container_args = job['kwargs']['container_args']
        self.assertEqual(container_args[0], 'data')
        # TODO
