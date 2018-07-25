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
        from girder.plugins import worker
        from girder.plugins.worker import utils as worker_utils
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
        self._origWorkerGetWorkerApiUrl = worker.getWorkerApiUrl

        rest.getCurrentToken = getCurrentToken
        rest.getApiUrl = lambda x: '/api/v1'
        rest.setCurrentUser(self.admin)
        worker.getWorkerApiUrl = worker_utils.getWorkerApiUrl = getWorkerApiUrl

    def tearDown(self):
        from girder.api import rest
        from girder.plugins import worker
        from girder.plugins.worker import utils as worker_utils

        rest.getCurrentToken = self._origRestGetCurrentToken
        rest.getApiUrl = self._origRestGetApiUrl
        worker.getWorkerApiUrl = worker_utils.getWorkerApiUrl = self._origWorkerGetWorkerApiUrl
        base.TestCase.tearDown(self)

    def test_genHandlerToRunDockerCLI(self):
        from girder.plugins.slicer_cli_web import docker_resource
        from girder.plugins.slicer_cli_web import rest_slicer_cli

        xmlpath = os.path.join(os.path.dirname(__file__), 'data', 'ExampleSpec.xml')
        cliXML = open(xmlpath, 'rb').read()
        resource = docker_resource.DockerResource('test')
        handlerFunc = rest_slicer_cli.genHandlerToRunDockerCLI(
            'dockerImage', 'data', cliXML, resource)
        self.assertIsNotNone(handlerFunc)

        job = handlerFunc(params={
            'inputImageFile_girderFileId': str(self.file['_id']),
            'secondImageFile_girderFileId': str(self.file['_id']),
            'outputStainImageFile_1_girderFolderId': str(self.folder['_id']),
            'outputStainImageFile_1_name': 'sample1.png',
            'outputStainImageFile_2_girderFolderId': str(self.folder['_id']),
            'outputStainImageFile_2_name': 'sample2.png',
            'stainColor_1': '[0.5, 0.5, 0.5]',
            'stainColor_2': '[0.2, 0.3, 0.4]',
            'returnparameterfile_girderFolderId': str(self.folder['_id']),
            'returnparameterfile_name': 'output.data',
        })
        self.assertHasKeys(
            job['kwargs']['inputs'],
            ['inputImageFile', 'stainColor_1', 'stainColor_2'])
        self.assertEqual(job['kwargs']['inputs']['inputImageFile']['id'], str(self.file['_id']))
        self.assertEqual(job['kwargs']['inputs']['stainColor_1']['data'], '[0.5, 0.5, 0.5]')
        self.assertEqual(job['kwargs']['inputs']['stainColor_1']['type'], 'number_list')
        self.assertHasKeys(
            job['kwargs']['outputs'],
            ['outputStainImageFile_1', 'outputStainImageFile_2', 'returnparameterfile'])
        self.assertEqual(len(job['kwargs']['task']['inputs']), 5)
        self.assertEqual(len(job['kwargs']['task']['outputs']), 3)
