"""Girder Worker task for CLI tasks."""
from girder_worker.app import app
from girder_worker.docker.tasks import docker_run

from .cli_utils import as_model


@app.task
def run(cliXML, **kwargs):
    clim = as_model(cliXML)
    print(clim, kwargs)


def _createIndexedParamTaskSpec(param):
    """Creates task spec for indexed parameters

    Parameters
    ----------
    param : ctk_cli.CLIParameter
        parameter for which the task spec should be created

    """

    curTaskSpec = dict()
    curTaskSpec['id'] = param.identifier()
    curTaskSpec['name'] = param.label
    curTaskSpec['type'] = _SLICER_TO_GIRDER_WORKER_TYPE_MAP[param.typ]
    curTaskSpec['format'] = _SLICER_TO_GIRDER_WORKER_TYPE_MAP[param.typ]

    if param.isExternalType():
        curTaskSpec['target'] = 'filepath'  # check

    return curTaskSpec


def _addIndexedOutputParamsToTaskSpec(index_output_params, taskSpec, hargs):

    for param in index_output_params:

        # add to task spec
        curTaskSpec = _createIndexedParamTaskSpec(param)

        curTaskSpec['path'] = hargs['params'][param.identifier() + _girderOutputNameSuffix]

        taskSpec['outputs'].append(curTaskSpec)

def _createOptionalParamTaskSpec(param):
    """Creates task spec for optional parameters

    Parameters
    ----------
    param : ctk_cli.CLIParameter
        parameter for which the task spec should be created

    """

    curTaskSpec = dict()
    curTaskSpec['id'] = param.identifier()
    if getattr(param, 'label', None):
        curTaskSpec['name'] = param.label
    curTaskSpec['type'] = _SLICER_TO_GIRDER_WORKER_TYPE_MAP[param.typ]
    curTaskSpec['format'] = _SLICER_TO_GIRDER_WORKER_TYPE_MAP[param.typ]

    if param.isExternalType():
        curTaskSpec['target'] = 'filepath'

    if param.channel != 'output':

        defaultValSpec = dict()
        defaultValSpec['format'] = curTaskSpec['format']
        defaultValSpec['data'] = _getParamDefaultVal(param)
        curTaskSpec['default'] = defaultValSpec

    return curTaskSpec



def _addOptionalInputParamsToTaskSpec(opt_input_params, taskSpec):

    for param in opt_input_params:

        # add to task spec
        curTaskSpec = _createOptionalParamTaskSpec(param)
        taskSpec['inputs'].append(curTaskSpec)

def _addOptionalOutputParamsToTaskSpec(opt_output_params, taskSpec, hargs):

    for param in opt_output_params:
        # set path if it was requested in the REST request
        if (param.identifier() + _girderOutputFolderSuffix not in hargs['params'] or
                param.identifier() + _girderOutputNameSuffix not in hargs['params']):
            continue

        # add to task spec
        curTaskSpec = _createOptionalParamTaskSpec(param)

        curTaskSpec['path'] = hargs['params'][param.identifier() + _girderOutputNameSuffix]

        taskSpec['outputs'].append(curTaskSpec)



def _addReturnParameterFileParamToTaskSpec(taskSpec, hargs):

    curName = _return_parameter_file_name
    curType = 'file'

    # check if return parameter file was requested in the REST request
    if (curName + _girderOutputFolderSuffix not in hargs['params'] or
            curName + _girderOutputNameSuffix not in hargs['params']):
        return

    # add to task spec
    curTaskSpec = dict()
    curTaskSpec['id'] = curName
    curTaskSpec['type'] = _SLICER_TO_GIRDER_WORKER_TYPE_MAP[curType]
    curTaskSpec['format'] = _SLICER_TO_GIRDER_WORKER_TYPE_MAP[curType]
    curTaskSpec['target'] = 'filepath'  # check
    curTaskSpec['path'] = hargs['params'][curName + _girderOutputNameSuffix]

    taskSpec['outputs'].append(curTaskSpec)


def _createInputParamBindingSpec(param, hargs, token):

    curBindingSpec = dict()
    if _is_on_girder(param):
        curBindingSpec = wutils.girderInputSpec(
            hargs[param.identifier()],
            resourceType=_SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ],
            dataType='string', dataFormat='string',
            token=token, fetchParent=False)
    else:
        # inputs that are not of type image, file, or directory
        # should be passed inline as string from json.dumps()
        curBindingSpec['mode'] = 'inline'
        curBindingSpec['type'] = _SLICER_TO_GIRDER_WORKER_TYPE_MAP[param.typ]
        curBindingSpec['format'] = 'json'
        curBindingSpec['data'] = hargs['params'][param.identifier()]

    return curBindingSpec


def _createOutputParamBindingSpec(param, hargs, user, token):

    curBindingSpec = wutils.girderOutputSpec(
        hargs[param.identifier()],
        token,
        name=hargs['params'][param.identifier() + _girderOutputNameSuffix],
        dataType='string', dataFormat='string'
    )

    if param.isExternalType() and param.reference is not None:

        if param.reference not in hargs:
            raise Exception(
                'Error: The specified reference attribute value'
                '%s for parameter %s is not a valid input' % (
                    param.reference, param.identifier())
            )

        curBindingSpec['reference'] = json.dumps({
            'itemId': str(hargs[param.reference]['_id']),
            'userId': str(user['_id']),
            'identifier': param.identifier()
        })

    return curBindingSpec


def _addIndexedInputParamBindings(index_input_params, bspec, hargs, token):

    for param in index_input_params:
        bspec[param.identifier()] = _createInputParamBindingSpec(param, hargs, token)


def _addIndexedOutputParamBindings(index_output_params,
                                   bspec, hargs, user, token):

    for param in index_output_params:
        bspec[param.identifier()] = _createOutputParamBindingSpec(
            param, hargs, user, token)


def _addOptionalInputParamBindings(opt_input_params, bspec, hargs, user, token):

    for param in opt_input_params:

        if _is_on_girder(param):
            suffix = _SLICER_TYPE_TO_GIRDER_INPUT_SUFFIX_MAP[param.typ]
            if param.identifier() + suffix not in hargs['params']:
                continue

            curModelName = _SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ]
            curModel = ModelImporter.model(curModelName)
            curId = hargs['params'][param.identifier() + suffix]

            hargs[param.identifier()] = curModel.load(id=curId,
                                                      level=AccessType.READ,
                                                      user=user)
        if param.identifier() in hargs['params']:
            bspec[param.identifier()] = _createInputParamBindingSpec(param, hargs, token)


def _addOptionalOutputParamBindings(opt_output_params,
                                    bspec, hargs, user, token):

    for param in opt_output_params:

        if not _is_on_girder(param):
            continue

        # check if it was requested in the REST request
        if (param.identifier() + _girderOutputFolderSuffix not in hargs['params'] or
                param.identifier() + _girderOutputNameSuffix not in hargs['params']):
            continue

        curModel = ModelImporter.model('folder')
        curId = hargs['params'][param.identifier() + _girderOutputFolderSuffix]
        doc = curModel.load(id=curId, level=AccessType.WRITE, user=user)
        if doc:
            hargs[param.identifier()] = doc

        if param.identifier() in hargs:
            bspec[param.identifier()] = _createOutputParamBindingSpec(param, hargs, user, token)


def _addReturnParameterFileBinding(bspec, hargs, user, token, job):

    curName = _return_parameter_file_name

    # check if return parameter file was requested in the REST request
    if (curName + _girderOutputFolderSuffix not in hargs['params'] or
            curName + _girderOutputNameSuffix not in hargs['params']):
        return

    curModel = ModelImporter.model('folder')
    curId = hargs['params'][curName + _girderOutputFolderSuffix]

    hargs[curName] = curModel.load(id=curId,
                                   level=AccessType.WRITE,
                                   user=user)

    curBindingSpec = wutils.girderOutputSpec(
        hargs[curName],
        token,
        name=hargs['params'][curName + _girderOutputNameSuffix],
        dataType='string', dataFormat='string',
        reference=json.dumps({
            'type': 'slicer_cli.parameteroutput',
            'jobId': str(job['_id'])
        })
    )

    bspec[curName] = curBindingSpec


def _is_on_girder(param):
    return param.typ in _SLICER_TYPE_TO_GIRDER_MODEL_MAP


def _getParamCommandLineValue(param, value):
    if isinstance(value, six.binary_type):
        value = value.decode('utf8')
    if param.isVector():
        cmdVal = '%s' % ', '.join(map(str, json.loads(value)))
    else:
        cmdVal = str(json.loads(value))

    return cmdVal


def _addOptionalInputParamsToContainerArgs(opt_input_params,
                                           containerArgs, hargs):

    for param in opt_input_params:

        if param.longflag:
            curFlag = param.longflag
        elif param.flag:
            curFlag = param.flag
        else:
            continue

        if _is_on_girder(param) and param.identifier() in hargs:

            curValue = "$input{%s}" % param.identifier()

        elif param.identifier() in hargs['params']:

            try:
                curValue = _getParamCommandLineValue(
                    param, hargs['params'][param.identifier()])
            except Exception:
                logger.exception(
                    'Error: Parameter value is not in json.dumps format\n'
                    '  Parameter name = %r\n  Parameter type = %r\n'
                    '  Value passed = %r', param.identifier(), param.typ,
                    hargs['params'][param.identifier()])
                raise
        else:
            continue

        containerArgs.append(curFlag)
        containerArgs.append(curValue)


def _addOptionalOutputParamsToContainerArgs(opt_output_params,
                                            containerArgs, kwargs, hargs):
    for param in opt_output_params:

        if param.longflag:
            curFlag = param.longflag
        elif param.flag:
            curFlag = param.flag
        else:
            continue
        if _is_on_girder(param) and param.identifier() in kwargs['outputs']:

            curValue = os.path.join(
                _worker_docker_data_dir,
                hargs['params'][param.identifier() + _girderOutputNameSuffix]
            )

            containerArgs.append(curFlag)
            containerArgs.append(curValue)


def _addReturnParameterFileToContainerArgs(containerArgs, kwargs, hargs):

    curName = _return_parameter_file_name

    if curName in kwargs['outputs']:

        curFlag = '--returnparameterfile'

        curValue = os.path.join(
            _worker_docker_data_dir,
            hargs['params'][curName + _girderOutputNameSuffix]
        )

        containerArgs.append(curFlag)
        containerArgs.append(curValue)


def _addIndexedParamsToContainerArgs(index_params, containerArgs, hargs):

    for param in index_params:

        if param.channel != 'output':

            if _is_on_girder(param):
                curValue = "$input{%s}" % param.identifier()
            else:
                curValue = _getParamCommandLineValue(
                    param,
                    hargs['params'][param.identifier()]
                )

        else:

            if not _is_on_girder(param):
                raise Exception(
                    'The type of indexed output parameter %d '
                    'must be of type - %s' % (
                        param.index,
                        _SLICER_TYPE_TO_GIRDER_MODEL_MAP.keys()
                    )
                )

            curValue = os.path.join(
                _worker_docker_data_dir,
                hargs['params'][param.identifier() + _girderOutputNameSuffix]
            )

        containerArgs.append(curValue)
