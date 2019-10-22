from os import access, R_OK
from os.path import basename, isfile, abspath, join

from girder_worker.app import app
from girder_worker.docker.transforms import BindMountVolume
from girder_worker.docker.transforms.girder import GirderFileIdToVolume
from girder_worker.docker.tasks import docker_run, DockerTask
from girder_worker_utils import _walk_obj


def _get_basename(direct_path):
    if not direct_path:
        return None
    return basename(direct_path)


TEMP_VOLUME_DIRECT_MOUNT_PREFIX = '/mnt/girder_direct_worker'


class DirectGirderFileIdToVolume(GirderFileIdToVolume):
    def __init__(self, _id, filename=None, direct_file_path=None, **kwargs):
        super(DirectGirderFileIdToVolume, self).__init__(_id, filename=filename or _get_basename(direct_file_path), **kwargs)
        self._direct_file_path = direct_file_path
        self._direct_container_path = None

    def resolve_direct_file_path(self):
        if not self._direct_file_path:
            return None

        path = abspath(self._direct_file_path)
        if isfile(path) and access(path, R_OK):
            self._direct_container_path = join(TEMP_VOLUME_DIRECT_MOUNT_PREFIX, self._filename)
            return BindMountVolume(path, self._direct_container_path, mode='ro')
        return None

    def transform(self, **kwargs):
        if self._direct_container_path:
            return self._direct_container_path
        return super(DirectGirderFileIdToVolume, self).transform(**kwargs)


def _resolve_direct_file_paths(args, kwargs):
    extra_volumes = []

    def resolve(arg, **kwargs):
        if isinstance(arg, DirectGirderFileIdToVolume):
            path = arg.resolve_direct_file_path()
            if path:
                extra_volumes.append(path)
        return arg
    _walk_obj(args, resolve)
    _walk_obj(kwargs, resolve)

    return extra_volumes


class DirectDockerTask(DockerTask):
    def __call__(self, *args, **kwargs):
        extra_volumes = _resolve_direct_file_paths(args, kwargs)
        if extra_volumes:
            volumes = kwargs.setdefault('volumes', [])
            if isinstance(volumes, list):
                # list mode use
                volumes.extend(extra_volumes)
            else:
                for extra_volume in extra_volumes:
                    volumes.update(extra_volume._repr_json_())

        super(DirectDockerTask, self).__call__(*args, **kwargs)


@app.task(base=DirectDockerTask)
def run(*args, **kwargs):
    """Wraps docker_run to support direct mount volumnes."""
    return docker_run(*args, **kwargs)
