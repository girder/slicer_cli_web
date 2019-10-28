import pytest
from os.path import basename
from slicer_cli_web.girder_worker_plugin.direct_docker_run import DirectGirderFileIdToVolume, run, \
    TEMP_VOLUME_DIRECT_MOUNT_PREFIX


class MockedGirderClient:
    def getFile(self, *args, **kwargs):
        return dict(name='abc')

    def downloadFile(self, file_id, file_path):
        with open(file_path, 'w') as f:
            f.write('dummy')


@pytest.mark.plugin('slicer_cli_web')
def test_direct_docker_run(mocker, server, adminToken, file):
    from girder.models.file import File

    docker_run_mock = mocker.patch('girder_worker.docker.tasks._docker_run')
    docker_run_mock.return_value = []

    gc_mock = MockedGirderClient()

    path = File().getLocalFilePath(file)

    run(image='test', container_args=[DirectGirderFileIdToVolume(
        file['_id'], filename=basename(path), direct_file_path=None, gc=gc_mock)])
    docker_run_mock.assert_called_once()
    args = docker_run_mock.call_args[0]
    # image
    assert args[1] == 'test'
    # container args
    assert len(args[4]) == 1
    assert args[4][0].endswith(basename(path))
    # volumes
    assert len(args[5]) == 2

    target_path = '%s/%s' % (TEMP_VOLUME_DIRECT_MOUNT_PREFIX, basename(path))

    docker_run_mock.reset_mock()

    run(image='test', container_args=[DirectGirderFileIdToVolume(
        file['_id'], direct_file_path=path, gc=gc_mock)])

    docker_run_mock.assert_called_once()
    args = docker_run_mock.call_args[0]
    # image
    assert args[1] == 'test'
    # container args
    assert args[4] == [target_path]
    # volumes
    assert len(args[5]) == 3

