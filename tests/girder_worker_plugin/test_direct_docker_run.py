import mock
import pytest
from os.path import basename
from slicer_cli_web.girder_worker_plugin.direct_docker_run import DirectGirderFileIdToVolume, run, \
    TEMP_VOLUME_DIRECT_MOUNT_PREFIX


class FakeAsyncResult(object):
    def __init__(self):
        self.task_id = 'fake_id'


@pytest.mark.plugin('slicer_cli_web')
@mock.patch('celery.Celery')
@mock.patch('girder_worker.docker.tasks._docker_run')
@mock.patch('girder_client.GirderClient')
def test_direct_docker_run(celery_mock, docker_run_mock, gc_mock, server, file):
    from girder.models.file import File

    instance = celery_mock.return_value
    instance.send_task.return_value = FakeAsyncResult()
    docker_run_mock.return_value = []

    path = File().getLocalFilePath(file)

    run.delay(image='test', container_args=[DirectGirderFileIdToVolume(
        file['_id'], filename=basename(path), direct_file_path=None, gc=gc_mock)])

    docker_run_mock.assert_called_once()
    assert docker_run_mock.call_args.args[1] == 'test'
    # container args
    assert docker_run_mock.call_args.args[4] == ['/mnt/girder_worker/%s' % basename(path)]
    # volumes
    assert len(docker_run_mock.call_args.args[5]) == 1

    target_path = '%s/%s' % (TEMP_VOLUME_DIRECT_MOUNT_PREFIX, basename(path))

    run.delay(image='test', container_args=[DirectGirderFileIdToVolume(
        file['_id'], direct_file_path=path, gc=gc_mock)])

    docker_run_mock.assert_called_once()
    assert docker_run_mock.call_args.args[1] == 'test'
    # container args
    assert docker_run_mock.call_args.args[4] == [target_path]
    # volumes
    assert len(docker_run_mock.call_args.args[5]) == 2

