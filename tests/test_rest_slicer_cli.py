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
        import girder_worker
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
        self._origWorkerGetWorkerApiUrl = girder_worker.getWorkerApiUrl

        rest.getCurrentToken = getCurrentToken
        rest.getApiUrl = lambda x: '/api/v1'
        rest.setCurrentUser(self.admin)
        girder_worker.getWorkerApiUrl = worker_utils.getWorkerApiUrl = getWorkerApiUrl

    def teardown_method(self, method):
        from girder.api import rest
        import girder_worker
        from girder_worker import utils as worker_utils

        rest.getCurrentToken = self._origRestGetCurrentToken
        rest.getApiUrl = self._origRestGetApiUrl
        girder_worker.getWorkerApiUrl = self._origWorkerGetWorkerApiUrl
        worker_utils.getWorkerApiUrl = self._origWorkerGetWorkerApiUrl

    @pytest.mark.plugin('sclicer_cli_web')
    def test_genHandlerToRunDockerCLI(self, admin, folder, file):
        from slicer_cli_web import docker_resource
        from slicer_cli_web import rest_slicer_cli
        from slicer_cli_web.models import CLIItem
        from girder.models.item import Item

        xmlpath = os.path.join(os.path.dirname(__file__), 'data', 'ExampleSpec.xml')

        girderCLIItem = Item().createItem('data', admin, folder)
        Item().setMetadata(girderCLIItem, dict(slicerCLIType='task', type='python',
                                               xml=open(xmlpath, 'rb').read()))

        resource = docker_resource.DockerResource('test')
        item = CLIItem(girderCLIItem)
        handlerFunc = rest_slicer_cli.genHandlerToRunDockerCLI(
            'dockerImage', CLIItem(item), resource)
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

        assert 'container_args' in job['kwargs']
        assert 'image' in job['kwargs']
        assert 'pull_image' in job['kwargs']

        assert job['kwargs']['image'] == 'dockerImage'
        assert not job['kwargs']['pull_image']
        container_args = job['kwargs']['container_args']
        assert container_args[0] == 'data'
