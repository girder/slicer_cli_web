import os
import pytest


@pytest.fixture
def folder(admin):
    from girder.models.folder import Folder
    f = Folder().createFolder(admin, 'folder', parentType='user')

    yield f


@pytest.fixture
def item(folder, admin):
    from girder.models.item import Item
    f = Item().createItem('item', admin, folder)

    yield f


@pytest.fixture
def file(item, admin, fsAssetstore):
    from girder.models.file import File
    f = File().createFile(admin, item, 'file', 7, fsAssetstore)

    yield f


class TestClass:
    def setup_method(self, method):
        import datetime

        from girder.api import rest
        from girder_worker.girder_plugin import utils
        from girder_worker import utils as worker_utils

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
        self._origWorkerGetWorkerApiUrl = utils.getWorkerApiUrl

        rest.getCurrentToken = getCurrentToken
        rest.getApiUrl = lambda x: '/api/v1'
        utils.getWorkerApiUrl = worker_utils.getWorkerApiUrl = getWorkerApiUrl

    def teardown_method(self, method):
        from girder.api import rest
        from girder_worker.girder_plugin import utils
        from girder_worker import utils as worker_utils

        rest.getCurrentToken = self._origRestGetCurrentToken
        rest.getApiUrl = self._origRestGetApiUrl
        utils.getWorkerApiUrl = self._origWorkerGetWorkerApiUrl
        worker_utils.getWorkerApiUrl = self._origWorkerGetWorkerApiUrl

    @pytest.mark.plugin('slicer_cli_web')
    def test_genHandlerToRunDockerCLI(self, admin, folder, file):
        from girder.api import rest
        from slicer_cli_web import docker_resource
        from slicer_cli_web import rest_slicer_cli
        from slicer_cli_web.models import CLIItem
        from girder.models.item import Item
        import json

        self.admin = admin
        rest.setCurrentUser(admin)
        xmlpath = os.path.join(os.path.dirname(__file__), 'data', 'ExampleSpec.xml')

        girderCLIItem = Item().createItem('data', admin, folder)
        Item().setMetadata(girderCLIItem, dict(slicerCLIType='task', type='python',
                                               xml=open(xmlpath, 'rb').read()))

        resource = docker_resource.DockerResource('test')
        item = CLIItem(girderCLIItem)
        handlerFunc = rest_slicer_cli.genHandlerToRunDockerCLI(
            'dockerImage', 'dockerImage@sha256:abc', item, resource)
        assert handlerFunc is not None

        job = handlerFunc(params={
            'inputImageFile': str(file['_id']),
            'secondImageFile': str(file['_id']),
            'outputStainImageFile_1_folder': str(folder['_id']),
            'outputStainImageFile_1': 'sample1.png',
            'outputStainImageFile_2_folder': str(folder['_id']),
            'outputStainImageFile_2_name': 'sample2.png',
            'stainColor_1': '[0.5, 0.5, 0.5]',
            'stainColor_2': '[0.2, 0.3, 0.4]',
            'returnparameterfile_folder': str(folder['_id']),
            'returnparameterfile': 'output.data',
        })

        kwargs = json.loads(job['kwargs'])
        assert 'container_args' in kwargs
        assert 'image' in kwargs
        assert 'pull_image' in kwargs

        print(kwargs)

        assert kwargs['image'] == 'dockerImage@sha256:abc'
        assert kwargs['pull_image'] == 'if-not-present'
        container_args = kwargs['container_args']
        assert container_args[0] == 'data'
