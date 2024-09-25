import subprocess

from girder import logger

from .utils import generate_image_name_for_singularity


class SingularityCommands:
    @staticmethod
    def singularity_version():
        """
        This method is used to check whether apptainer is currently installed on the system.
        """
        return ['apptainer', '--version']

    @staticmethod
    def singularity_pull(name: str, uri: str = 'docker'):
        """
        This method is used to generate the command for the singualrity pull function for pulling
        images from online.
        Args:
        name(str.required) - image name and tag as a single string '<image_name>:<tag>'
        uri(str, optional) - image uri (necessary for Dockerhub)

        Returns:
        List of strings for singularity subprocess command.
        """
        sif_name = generate_image_name_for_singularity(name)
        return ['apptainer', 'pull', '--force', sif_name, f'{uri}://{name}']

    @staticmethod
    def singualrity_run(imageName: str, run_parameters=None, container_args=None):
        sif_name = generate_image_name_for_singularity(imageName)
        cmd = ['apptainer', 'run', '--no-mount', '/cmsuf']
        if run_parameters:
            run_parameters = run_parameters.split(' ')
            cmd.extend(run_parameters)
        cmd.append(sif_name)
        if container_args:
            container_args = container_args.split(' ')
            cmd.extend(container_args)
        return cmd

    @staticmethod
    def singularity_get_env(image: str, run_parameters=None):
        sif_name = generate_image_name_for_singularity(image)
        cmd = ['apptainer', 'exec', '--cleanenv']
        if run_parameters:
            run_parameters = run_parameters.split(' ')
            cmd.extend(run_parameters)
        cmd.append(sif_name)
        cmd.append('env')
        return cmd

    @staticmethod
    def singularity_inspect(imageName, option='-l', json_format=True):
        """
        This function is used to get the apptainer command for inspecting the sif file. By default,
        it inspects the labels in a json format, but you can you any option allowed by apptainer
        by setting the option flag appropriately and also the json flag is set to True by default.
        """
        sif_name = generate_image_name_for_singularity(imageName)
        cmd = ['apptainer', 'inspect']
        if json_format:
            cmd.append('--json')
        cmd.append(option)
        cmd.append(sif_name)
        return cmd


def run_command(cmd):
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if isinstance(res.stdout, bytes):
            res = res.stdout.decode('utf-8')
        res = res.strip()
        return res
    except Exception as e:
        logger.exception(f'Error occured when running command {cmd} - {e}')
        raise Exception(f'Error occured when running command {cmd} - {e}')
