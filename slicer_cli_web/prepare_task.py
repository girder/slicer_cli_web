import json
import six

from girder.api.rest import RestException
from girder.utility.model_importer import ModelImporter
from girder import logger
from girder.constants import AccessType
from girder_worker.docker.transforms import VolumePath
from girder_worker.docker.transforms.girder import GirderUploadVolumePathToFolder, GirderFileIdToVolume, GirderFolderIdToVolume
from girder_worker.girder_plugin.constants import PluginSettings
from girder.exceptions import FilePathException
from girder.models.file import File
from girder.models.setting import Setting

from .direct_docker_run import DirectGirderFileIdToVolume

from .cli_utils import \
    SLICER_TYPE_TO_GIRDER_MODEL_MAP, is_on_girder, return_parameter_file_name


OPENAPI_DIRECT_TYPES = set(['boolean', 'integer', 'float', 'double', 'string'])


def _to_file_volume(param, model):
    girder_type = SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ]

    if girder_type != 'file':
        return GirderFolderIdToVolume(model['_id'])

    if not Setting().get(PluginSettings.DIRECT_PATH):
        return GirderFileIdToVolume(model['_id'])

    try:
        path = File().getLocalFilePath(model)
        return DirectGirderFileIdToVolume(model['_id'], direct_file_path=path)
    except FilePathException:
        return GirderFileIdToVolume(model['_id'])


def _parseParamValue(param, value, user, token):
    if isinstance(value, six.binary_type):
        value = value.decode('utf8')

    param_id = param.identifier()
    if is_on_girder(param):
        girder_type = SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ]
        curModel = ModelImporter.model(girder_type)
        loaded = curModel.load(value, level=AccessType.READ, user=user)
        if not loaded:
            raise RestException('Invalid %s id (%s).' % (curModel.name, str(value)))
        return loaded

    try:
        if param.isVector():
            return '%s' % ', '.join(map(str, json.loads(value)))
        elif param.typ in OPENAPI_DIRECT_TYPES or param.typ == 'string-enumeration':
            return str(value)
        else:  # json
            return str(json.loads(value))
    except json.JSONDecodeError:
        msg = 'Error: Parameter value is not in json.dumps format\n' \
              '  Parameter name = %r\n  Parameter type = %r\n' \
             '  Value passed = %r' % (param_id, param.typ, value)
        logger.exception(msg)
        raise RestException(msg)


def _add_optional_input_param(param, args, user, token):
    if param.identifier() not in args:
        return []
    value = _parseParamValue(param, args[param.identifier()], user, token)

    container_args = []
    if param.longflag:
        container_args.append(param.longflag)
    elif param.flag:
        container_args.append(param.flag)
    else:
        return []

    if is_on_girder(param):
        # Bindings
        container_args.append(_to_file_volume(param, value))
    else:
        container_args.append(value)
    return container_args


def _add_optional_output_param(param, args, user):
    if not param.isExternalType() or not is_on_girder(param) \
       or param.identifier() not in args or \
       (param.identifier() + '_folder') not in args:
        return []
    value = args[param.identifier()]
    folder = args[param.identifier() + '_folder']

    container_args = []
    if param.longflag:
        container_args.append(param.longflag)
    elif param.flag:
        container_args.append(param.flag)
    else:
        return []

    folderModel = ModelImporter.model('folder')
    instance = folderModel.load(folder, level=AccessType.WRITE, user=user)
    if not instance:
        raise RestException('Invalid Folder id (%s).' % (str(folder)))

    # Output Binding !!
    path = VolumePath(value)
    container_args.append(GirderUploadVolumePathToFolder(path, folder))

    return container_args


def _add_indexed_input_param(param, args, user, token):
    value = _parseParamValue(param, args[param.identifier()], user, token)

    if is_on_girder(param):
        # Bindings
        return _to_file_volume(param, value)
    return value


def _add_indexed_output_param(param, args, user):
    value = args[param.identifier()]
    folder = args[param.identifier() + '_folder']

    folderModel = ModelImporter.model('folder')
    instance = folderModel.load(folder, level=AccessType.WRITE, user=user)
    if not instance:
        raise RestException('Invalid Folder id (%s).' % (str(folder)))

    # Output Binding !!
    path = VolumePath(value)
    return GirderUploadVolumePathToFolder(path, folder)


def prepare_task(params, user, token, index_params, opt_params, has_simple_return_file):
    ca = []

    # optional params
    for param in opt_params:
        if param.channel == 'output':
            ca.extend(_add_optional_output_param(param, params, user, token))
        else:
            ca.extend(_add_optional_input_param(param, params, user, token))

    if has_simple_return_file:
        param_id = return_parameter_file_name + '_folder'
        param_name_id = return_parameter_file_name
        if param_id in params and param_name_id in params:
            value = params[return_parameter_file_name]
            folder = params[return_parameter_file_name + '_folder']

            folderModel = ModelImporter.model('folder')
            instance = folderModel.load(folder, level=AccessType.WRITE, user=user)
            if not instance:
                raise RestException('Invalid Folder id (%s).' % (str(folder)))

            ca.append('--returnparameterfile')

            # Output Binding !!
            path = VolumePath(value)
            ca.append(GirderUploadVolumePathToFolder(path, folder))

    # indexed params
    for param in index_params:
        if param.channel == 'output':
            ca.append(_add_indexed_output_param(param, params, user))
        else:
            ca.append(_add_indexed_input_param(param, params, user, token))

    return ca
