"""Girder Worker task for CLI tasks."""
from girder_worker.app import app
from girder_worker.docker.tasks import docker_run
from girder_worker.docker.transforms import VolumePath
from girder_worker.docker.transforms.girder import GirderFileIdToVolume, \
  GirderUploadVolumePathToFolder

from .cli_utils import as_model, get_cli_parameters, is_on_girder, \
  return_parameter_file_name


def _add_optional_input_param(param, args, container_args):
    if param.identifier() not in args:
        return
    value = args[param.identifier()]

    if param.longflag:
        container_args.append(param.longflag)
    elif param.flag:
        container_args.append(param.flag)
    else:
        return

    if is_on_girder(param):
        # Bindings
        container_args.append(GirderFileIdToVolume(value))
    else:
        container_args.append(value)


def _add_optional_output_param(param, args, container_args):
    if not param.isExternalType() or not is_on_girder(param) \
        or param.identifier() not in args or \
        (param.identifier() + '_folder') not in args:
        return
    value = args[param.identifier()]
    folder = args[param.identifier() + '_folder']

    if param.longflag:
        container_args.append(param.longflag)
    elif param.flag:
        container_args.append(param.flag)
    else:
        return

    # Output Binding !!
    path = VolumePath(value)
    container_args.append(GirderUploadVolumePathToFolder(path, folder))


@app.task
def run(cliXML, dockerImage, cliRelPath, args):
    clim = as_model(cliXML)

    index_params, opt_params, simple_out_params = get_cli_parameters(clim)
    opt_input_params = [p for p in opt_params if p.channel != 'output']
    opt_output_params = [p for p in opt_params if p.channel == 'output']
    has_simple_return_file = len(simple_out_params) > 0

    container_args = [cliRelPath]

    # optional input params
    for param in opt_input_params:
        _add_optional_input_param(param, args, container_args)

    # optional output params
    for param in opt_output_params:
        _add_optional_output_param(param, args, container_args)

    # add returnparameterfile if there are simple output params
    if has_simple_return_file and return_parameter_file_name in args and \
       (return_parameter_file_name + '_folder') in args:
        value = args[return_parameter_file_name]
        folder = args[return_parameter_file_name + '_folder']

        container_args.append('--returnparameterfile')

        # Output Binding !!
        path = VolumePath(value)
        container_args.append(GirderUploadVolumePathToFolder(path, folder))

    # indexed input params
    for param in index_params:
        if param.identifier() not in args:
            continue
        value = args[param.identifier()]

        if is_on_girder(param):
            # Bindings
            container_args.append(GirderFileIdToVolume(value))
        else:
            container_args.append(value)

    print(container_args)

    return docker_run.delay(dockerImage, pull_image=False,
                            container_args=container_args)
