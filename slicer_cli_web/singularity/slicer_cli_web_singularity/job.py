import json
import os
import subprocess

from girder import logger
from girder_jobs.models.job import Job

from slicer_cli_web.models import DockerImageError, DockerImageNotFoundError

from .commands import SingularityCommands, run_command
from .utils import (generate_image_name_for_singularity, sanitize_and_return_json,
                    switch_to_sif_image_folder)


def is_valid_path(path):
    """
    Check if the provided path is a valid and accessible path in the file system.

    Parameters:
    path (str): The path to check.

    Returns:
    bool: True if the path is valid and accessible, False otherwise.
    """
    return os.path.exists(path) and os.access(path, os.R_OK)


def is_singularity_installed(path=None):
    """
    This function is used to check whether singularity is availble on the target system.
    This function is useful to make sure that singularity is accessible from a SLURM job submitted
    to HiperGator

    Args:
        path (str, optional): If the user wants to provide a specific path where singularity is
                              installed, you can provide that path. Defaults to None.

    Returns:
    bool: True if singualrity is successfully accessible on the target system. False otherwise
    """
    try:
        logger.info('Checking path')
        if path and is_valid_path(path):
            os.chdir(path)
    except Exception:
        logger.exception(f'{path} is not a valid path')
        raise Exception(
            f'{path} is not a valid path'
        )
    try:
        subprocess.run(SingularityCommands.singularity_version(), check=True)
        logger.info('Singularity env available')
    except Exception as e:
        logger.info(f'Exception {e} occured')
        raise e


def find_local_singularity_image(name: str, path=''):
    """
    Check if the image is present locally on the system in a specified path. For our usecase, we
    insall the images to a specific path on /blue directory, which can be modified via the argument
    to the function

    Args:
        name(str, required) - The name of the docker image with the tag <image>:<tag>.
        path(str, optional) - This path refers to the path on the local file system designated for
                              placing singularity images after they are pulled from the interweb.
    Returns:
    bool: True if singularity image is avaialble on the given path on host system. False otherwise.

    """
    try:
        sif_name = generate_image_name_for_singularity(name)
    except Exception:
        logger.exception("There's an error with the image name. Please check again and try")
        raise Exception("There's an error with the image name. Please check again and try")
    if not path:
        path = os.getenv('SIF_IMAGE_PATH', '')
        if not is_valid_path(path):
            logger.exception(
                'Please provide a valid path or set the environment variable "SIF_IMAGE_PATH" and'
                'ensure the path has appropriate access')
            raise Exception(
                'Please provide a valid path or set the environment variable "SIF_IMAGE_PATH" and'
                'ensure the path has appropriate access')
    return os.path.exists(path + sif_name)


def pull_image_and_convert_to_sif(names):
    """
    This is the function similar to the pullDockerImage function that pulls the image from
    Dockerhub or other instances if it's supported in the future
    Args:
    names(List(str), required) -> The list of image names of the format <img>:<tag>

    Raises:
    If pulling of any of the images fails, the function raises an error with the list of images
    that failed.
    """
    failedImageList = []
    for name in names:
        try:
            logger.info(f'Starting to pull image {name}')
            pull_cmd = SingularityCommands.singularity_pull(name)
            subprocess.run(pull_cmd, check=True)
        except Exception as e:
            logger.info(f'Failed to pull image {name}: {e}')
            failedImageList.append(name)
    if len(failedImageList) != 0:
        raise DockerImageNotFoundError('Could not find multiple images ',
                                       image_name=failedImageList)


def load_meta_data_for_singularity(job, pullList, loadList, notExistSet):
    # flag to indicate an error occurred
    errorState = False
    images = []
    for name in pullList:
        if name not in notExistSet:
            job = Job().updateJob(
                job,
                log=f'Image {name} was pulled successfully \n',
            )

            try:
                cli_dict = get_cli_data_for_singularity(name, job)
                images.append((name, cli_dict))
                job = Job().updateJob(
                    job,
                    log=f'Got pulled image {name} metadata \n'

                )
            except DockerImageError as err:
                job = Job().updateJob(
                    job,
                    log=f'FAILURE: Error with recently pulled image {name}\n{err}\n',
                )
                errorState = True

    for name in loadList:
        # create dictionary and load to database
        try:
            cli_dict = get_cli_data_for_singularity(name, job)
            images.append((name, cli_dict))
            job = Job().updateJob(
                job,
                log=f'Loaded metadata from pre-existing local image {name}\n'
            )
        except DockerImageError as err:
            job = Job().updateJob(
                job,
                log=f'FAILURE: Error with recently loading pre-existing image {name}\n{err}\n',
            )
            errorState = True
    return images, errorState


def get_cli_data_for_singularity(name, job):
    try:
        # We want to mimic the behaviour of docker run <img>:<tag> --list_cli in singularity
        cli_dict = get_local_singularity_output(name, '--list_cli')
        # contains nested dict
        # {<cliname>:{type:<type>}}
        if isinstance(cli_dict, bytes):
            cli_dict = cli_dict.decode('utf8')
        cli_dict = json.loads(cli_dict)

        for key, info in cli_dict.items():
            desc_type = info.get('desc-type', 'xml')
            cli_desc = get_local_singularity_output(name, f'{key} --{desc_type}')

            if isinstance(cli_desc, bytes):
                cli_desc = cli_desc.decode('utf8')

            cli_dict[key][desc_type] = cli_desc
            job = Job().updateJob(
                job,
                log=f'Got image {name}, cli {key} metadata\n',
            )
        return cli_dict
    except Exception as err:
        logger.exception('Error getting %s cli data from image', name)
        raise DockerImageError('Error getting %s cli data from image ' % (name) + str(err))


def _is_nvidia_img(imageName):
    switch_to_sif_image_folder()
    inspect_labels_cmd = SingularityCommands.singularity_inspect(imageName)
    try:
        res = run_command(inspect_labels_cmd)
        res = sanitize_and_return_json(res)
        nvidia = res.get('com.nvidia.volumes.needed', None)
        if not nvidia:
            return False
        return True
    except Exception as e:
        raise Exception(f'Error occured {e.stderr.decode()}')


def _get_last_workdir(imageName):
    run_parameters = '--no-mount /cmsuf'
    switch_to_sif_image_folder()
    cmd = SingularityCommands.singularity_get_env(image=imageName, run_parameters=run_parameters)
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        res = res.stdout
        if isinstance(res, bytes):
            res = res.decode('utf-8').strip()
        entry_path_line = next((line for line in res.split('\n') if 'entry_path' in line), None)
        pwd = ''
        if entry_path_line:
            # Extract the value after '='
            pwd = entry_path_line.split('=')[1].strip()
        return pwd
    except Exception as e:
        raise Exception(f'Error occured {e.stderr.decode()}')


def get_local_singularity_output(imgName, cmdArg: str):
    """
    This function is used to run the singularity command locally for non-resource intensive tasks
    such as getting schema, environment variables and so on and return that output to the calling
    function
    """
    try:
        pwd = _get_last_workdir(imgName)
        if not pwd:
            logger.exception('Please set the entry_path env variable on the Docker Image')
            raise Exception('Please set the entry_path env variable on the Docker Image')
        run_parameters = f'--pwd {pwd}'
        cmd = SingularityCommands.singualrity_run(
            imgName, run_parameters=run_parameters, container_args=cmdArg)
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return res.stdout
    except Exception as e:
        raise Exception(f'error occured {e}')


def find_and_remove_local_sif_files(name: str, path=None):
    try:
        sif_name = generate_image_name_for_singularity(name)
    except Exception:
        logger.exception("There's an error with the image name. Please check again and try")
        raise Exception("There's an error with the image name. Please check again and try")
    if not path:
        path = os.getenv('SIF_IMAGE_PATH', '')
        if not is_valid_path(path):
            logger.exception(
                'Please provide a valid path or set the environment variable "SIF_IMAGE_PATH" and'
                'ensure the path has appropriate access')
            raise Exception(
                'Please provide a valid path or set the environment variable "SIF_IMAGE_PATH" and'
                'ensure the path has appropriate access')
        filename = os.path.join(path, sif_name)
        if os.path.exists(filename):
            os.remove(filename)
