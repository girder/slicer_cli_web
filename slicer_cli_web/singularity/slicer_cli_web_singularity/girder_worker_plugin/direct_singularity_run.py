import os
from uuid import uuid4

from girder import logger
from girder_worker.app import app
from girder_worker.docker.io import FDReadStreamConnector
from girder_worker_singularity.tasks import SingularityTask, singularity_run

from slicer_cli_web.girder_worker_plugin.cli_progress import CLIProgressCLIWriter
from slicer_cli_web.girder_worker_plugin.direct_docker_run import _resolve_direct_file_paths

from ..job import _get_last_workdir, _is_nvidia_img, generate_image_name_for_singularity


class DirectSingularityTask(SingularityTask):
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
        super().__call__(*args, **kwargs)


def check_local_sif_image(image):
    """
    Pulls the specified Plugin image (Ususally a docker image) onto the singularity container if the image is not present
    """
    # Image path - Image path has to be present in tmp/images folder
    if not image:
        logger.write('Image name cannot be empty')
        return False
    # Just for testing. Change it later...
    return False


@app.task(base=DirectSingularityTask, bind=True)
def run(task, **kwargs):
    """Wraps singularity_run to support running singularity containers"""
    image = kwargs['image']
    kwargs['image'] = generate_image_name_for_singularity(image)
    try:
        pwd = _get_last_workdir(image)
        kwargs['pwd'] = pwd
    except Exception as e:
        raise e
    logs_dir = os.getenv('LOGS')
    kwargs['nvidia'] = _is_nvidia_img(image)
    # Cahnge to reflect JOBID for logs later
    random_file_name = str(uuid4()) + 'logs.log'
    log_file_name = os.path.join(logs_dir, random_file_name)
    kwargs['log_file'] = log_file_name
    # Create file since it doesn't exist
    if not os.path.exists(log_file_name):
        with open(log_file_name, 'x'):
            pass
    file_obj = open(log_file_name, 'rb')
    if hasattr(task, 'job_manager'):
        stream_connectors = kwargs.setdefault('stream_connectors', [])
        stream_connectors.append(FDReadStreamConnector(
            input=file_obj,
            output=CLIProgressCLIWriter(task.job_manager)
        ))
    return singularity_run(task, **kwargs)
