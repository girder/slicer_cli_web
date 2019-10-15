import os
import json
import six
import sys

from girder.api.rest import Resource, boundHandler, \
    RestException, setResponseHeader, setRawResponse
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter
from girder import logger
from girder_worker.girder_plugin.utils import jobInfoSpec, girderInputSpec, \
    girderOutputSpec

from .cli_utils import as_model, generate_description, \
    SLICER_TYPE_TO_GIRDER_MODEL_MAP, \
    get_cli_parameters, is_on_girder, return_parameter_file_name


_return_parameter_file_desc = """
    Filename in which to write simple return parameters
    (integer, float, integer-vector, etc.) as opposed to bulk
    return parameters (image, file, directory, geometry,
    transform, measurement, table).
"""


def _parseParamValue(param, value, user, token, inputs):
    if isinstance(value, six.binary_type):
        value = value.decode('utf8')

    param_id = param.identifier()
    if is_on_girder(param):
        girder_type = SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ]
        curModel = ModelImporter.model(girder_type)
        loaded = curModel.load(value, level=AccessType.READ, user=user)
        if not loaded:
            raise RestException('Invalid %s id (%s).' % (curModel.name, str(value)))
        inputs.append(girderInputSpec(loaded, girder_type, token=token))
        return value

    try:
        if param.isVector():
            return '%s' % ', '.join(map(str, json.loads(value)))
        else:
            return str(json.loads(value))
    except Exception:
        logger.exception(
            'Error: Parameter value is not in json.dumps format\n'
            '  Parameter name = %r\n  Parameter type = %r\n'
            '  Value passed = %r', param_id, param.typ,
            value)
        raise


def _addIndexedInputParamsToHandler(index_input_params, handlerDesc):

    for param in index_input_params:

        # add to route description
        if param.isExternalType():
            handlerDesc.param(param.identifier(),
                              'Girder ID of input %s - %s: %s'
                              % (param.typ, param.identifier(), param.description),
                              dataType='string', required=True)
        else:
            handlerDesc.param(param.identifier(), param.description,
                              dataType='string', required=True)


def _addIndexedOutputParamsToHandler(index_output_params, handlerDesc):

    for param in index_output_params:

        # add param for parent folder to route description
        handlerDesc.param(param.identifier() + '_folder',
                          'Girder ID of parent folder '
                          'for output %s - %s: %s'
                          % (param.typ, param.typ, param.description),
                          dataType='string', required=True)

        # add param for name of current output to route description
        handlerDesc.param(param.identifier(),
                          'Name of output %s - %s: %s'
                          % (param.typ, param.identifier(), param.description),
                          dataType='string', required=True)


def _getParamDefaultVal(param):

    if param.default is not None:
        return param.default
    elif param.typ == 'boolean':
        return False
    elif param.isVector():
        return None
    elif param.isExternalType():
        return ""
    else:
        raise Exception(
            'optional parameters of type %s must '
            'provide a default value in the xml' % param.typ)


def _addOptionalInputParamsToHandler(opt_input_params, handlerDesc):

    for param in opt_input_params:

        # add to route description
        defaultVal = _getParamDefaultVal(param)

        if param.isExternalType():
            handlerDesc.param(param.identifier(),
                              'Girder ID of input %s - %s: %s'
                              % (param.typ, param.identifier(), param.description),
                              dataType='string',
                              required=False)
        else:
            handlerDesc.param(param.identifier(), param.description,
                              dataType='string',
                              default=json.dumps(defaultVal),
                              required=False)


def _addOptionalOutputParamsToHandler(opt_output_params, handlerDesc):

    for param in opt_output_params:

        if not param.isExternalType():
            continue

        # add param for parent folder to route description
        handlerDesc.param(param.identifier() + '_folder',
                          'Girder ID of parent folder '
                          'for output %s - %s: %s'
                          % (param.typ, param.identifier(), param.description),
                          dataType='string',
                          required=False)

        # add param for name of current output to route description
        handlerDesc.param(param.identifier(),
                          'Name of output %s - %s: %s'
                          % (param.typ, param.identifier(), param.description),
                          dataType='string', required=False)


def _addReturnParameterFileParamToHandler(handlerDesc):

    curName = return_parameter_file_name
    curType = 'file'
    curDesc = _return_parameter_file_desc

    # add param for parent folder to route description
    handlerDesc.param(curName + '_folder',
                      'Girder ID of parent folder '
                      'for output %s - %s: %s'
                      % (curType, curName, curDesc),
                      dataType='string',
                      required=False)

    # add param for name of current output to route description
    handlerDesc.param(curName,
                      'Name of output %s - %s: %s'
                      % (curType, curName, curDesc),
                      dataType='string', required=False)


def genHandlerToRunDockerCLI(dockerImage, cliRelPath, cliXML, restResource):
    """Generates a handler to run docker CLI using girder_worker

    Parameters
    ----------
    dockerImage : str
        Docker image in which the CLI resides
    cliRelPath : str
        Relative path of the CLI which is needed to run the CLI by running
        the command docker run `dockerImage` `cliRelPath`
    cliXML:str
        Cached copy of xml spec for this cli
    restResource : girder.api.rest.Resource
        The object of a class derived from girder.api.rest.Resource to which
        this handler will be attached

    Returns
    -------
    function
        Returns a function that runs the CLI using girder_worker

    """

    cliName = os.path.normpath(cliRelPath).replace(os.sep, '.')

    # get xml spec
    str_xml = cliXML

    clim = as_model(str_xml)

    # do stuff needed to create REST endpoint for cLI
    handlerDesc = Description(clim.title).notes(generate_description(clim))

    # get CLI parameters
    index_params, opt_params, simple_out_params = get_cli_parameters(clim)

    # add indexed input parameters
    index_input_params = [p for p in index_params if p.channel != 'output']

    _addIndexedInputParamsToHandler(index_input_params, handlerDesc)

    # add indexed output parameters
    index_output_params = [p for p in index_params if p.channel == 'output']

    _addIndexedOutputParamsToHandler(index_output_params, handlerDesc)

    # add optional input parameters
    opt_input_params = [p for p in opt_params if p.channel != 'output']

    _addOptionalInputParamsToHandler(opt_input_params, handlerDesc)

    # add optional output parameters
    opt_output_params = [p for p in opt_params if p.channel == 'output']

    _addOptionalOutputParamsToHandler(opt_output_params, handlerDesc)

    # add returnparameterfile if there are simple output params
    has_simple_return_file = len(simple_out_params) > 0
    if has_simple_return_file:
        _addReturnParameterFileParamToHandler(handlerDesc)

    # define CLI handler function
    @boundHandler(restResource)
    @access.user
    @describeRoute(handlerDesc)
    def cliHandler(self, params):
        user = self.getCurrentUser()
        jobModel = ModelImporter.model('job', 'jobs')
        # create job
        jobTitle = '.'.join((restResource.resourceName, cliName))
        job = jobModel.createJob(title=jobTitle,
                                 type=jobTitle,
                                 handler='worker_handler',
                                 user=user)
        token = jobModel.createJobToken(job)

        args = params.copy()
        inputs = []
        outputs = []

        for param in opt_input_params:
            param_id = param.identifier()
            if param_id in args:
                args[param_id] = _parseParamValue(param, args[param_id], user, token, inputs)

        folderModel = ModelImporter.model('folder')
        for param in opt_output_params:
            param_id = param.identifier() + '_folder'
            param_name_id = param.identifier()
            if not param.isExternalType() or param_id not in args or \
               param_name_id not in args:
                continue
            curId = args[param_id]
            instance = folderModel.load(curId, level=AccessType.WRITE, user=user)
            if not instance:
                raise RestException('Invalid Folder id (%s).' % (str(curId)))
            outputs.append(girderOutputSpec(instance, token=token))

        if has_simple_return_file:
            param_id = return_parameter_file_name + '_folder'
            param_name_id = return_parameter_file_name
            if param_id in args and param_name_id in args:
                curId = args[param_id]
                instance = folderModel.load(curId, level=AccessType.WRITE, user=user)
                if not instance:
                    raise RestException('Invalid Folder id (%s).' % (str(curId)))
                outputs.append(girderOutputSpec(instance, token=token))

        # verify parameters
        for param in index_input_params:
            param_id = param.identifier()
            args[param_id] = _parseParamValue(param, args[param_id], user, token, inputs)

        for param in index_output_params:
            param_id = param.identifier() + '_folder'
            curId = args[param_id]
            instance = folderModel.load(curId, level=AccessType.WRITE, user=user)
            if not instance:
                raise RestException('Invalid Folder id (%s).' % (str(curId)))
                outputs.append(girderOutputSpec(instance, token=token))

        job['token'] = token
        job['celeryTaskName'] = 'slicer_cli_web.image_worker_tasks.run'
        job['kwargs'] = {
            'cliXML': cliXML,
            'dockerImage': dockerImage,
            'cliRelPath': cliRelPath,
            'args': args,
            'inputs': inputs,
            'outputs': outputs,
            'jobInfo': jobInfoSpec(job, token)
        }



        job = jobModel.save(job)
        jobModel.scheduleJob(job)

        # return result
        return jobModel.filter(job, user)

    return cliHandler


def genHandlerToGetDockerCLIXmlSpec(cliRelPath, cliXML, restResource):
    """Generates a handler that returns the XML spec of the docker CLI

    Parameters
    ----------
    dockerImage : str
        Docker image in which the CLI resides
    cliRelPath : str
        Relative path of the CLI which is needed to run the CLI by running
        the command docker run `dockerImage` `cliRelPath`
    cliXML: str
        value of clispec stored in settings
    restResource : girder.api.rest.Resource
        The object of a class derived from girder.api.rest.Resource to which
        this handler will be attached

    Returns
    -------
    function
        Returns a function that returns the xml spec of the CLI

    """

    str_xml = cliXML
    if isinstance(str_xml, six.text_type):
        str_xml = str_xml.encode('utf8')

    # define the handler that returns the CLI's xml spec
    @boundHandler(restResource)
    @access.user
    @describeRoute(
        Description('Get XML spec of %s CLI' % cliRelPath)
    )
    def getXMLSpecHandler(self, *args, **kwargs):
        setResponseHeader('Content-Type', 'application/xml')
        setRawResponse()
        return str_xml

    return getXMLSpecHandler


def genRESTEndPointsForSlicerCLIsInDockerCache(restResource, dockerCache):
    """Generates REST end points for slicer CLIs placed in subdirectories of a
    given root directory and attaches them to a REST resource with the given
    name.

    For each CLI, it creates:
    * a GET Route (<apiURL>/`restResourceName`/<cliRelativePath>/xmlspec)
    that returns the xml spec of the CLI
    * a POST Route (<apiURL>/`restResourceName`/<cliRelativePath>/run)
    that runs the CLI

    It also creates a GET route (<apiURL>/`restResourceName`) that returns a
    list of relative routes to all CLIs attached to the generated REST resource

    Parameters
    ----------
    restResource : a dockerResource
        REST resource to which the end-points should be attached
    dockerCache : DockerCache object representing data stored in settings

    """

    # validate restResource argument
    if not isinstance(restResource, Resource):
        raise Exception('restResource must be a Docker Resource')

    for docker_image in dockerCache.getImages():
        dimg = docker_image.name
        # get CLI list
        cliListSpec = docker_image.getCLIListSpec()

        restPath = dimg.replace(':', '_').replace('/', '_').replace('@', '_')
        # Add REST end-point for each CLI
        for cliRelPath in cliListSpec.keys():
            # create a POST REST route that runs the CLI
            try:
                cliXML = docker_image.getCLIXML(cliRelPath)
                cliRunHandler = genHandlerToRunDockerCLI(
                    dimg, cliRelPath, cliXML, restResource)
            except Exception:
                logger.exception('Failed to create REST endpoints for %r',
                                 cliRelPath)
                continue

            cliSuffix = os.path.normpath(cliRelPath).replace(os.sep, '_')

            cliRunHandlerName = restPath+'_run_' + cliSuffix
            setattr(restResource, cliRunHandlerName, cliRunHandler)
            restResource.route('POST',
                               (restPath, cliRelPath, 'run'),
                               getattr(restResource, cliRunHandlerName))

            # store new rest endpoint
            restResource.storeEndpoints(
                dimg, cliRelPath, 'run', ['POST', (restPath, cliRelPath, 'run'),
                                          cliRunHandlerName])

            # create GET REST route that returns the xml of the CLI
            try:
                cliGetXMLSpecHandler = genHandlerToGetDockerCLIXmlSpec(
                    cliRelPath, cliXML,
                    restResource)
            except Exception:
                logger.exception('Failed to create REST endpoints for %s',
                                 cliRelPath)
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logger.error('%r', [exc_type, fname, exc_tb.tb_lineno])
                continue

            cliGetXMLSpecHandlerName = restPath+'_get_xml_' + cliSuffix
            setattr(restResource,
                    cliGetXMLSpecHandlerName,
                    cliGetXMLSpecHandler)
            restResource.route('GET',
                               (restPath, cliRelPath, 'xmlspec',),
                               getattr(restResource, cliGetXMLSpecHandlerName))

            restResource.storeEndpoints(
                dimg, cliRelPath, 'xmlspec',
                ['GET', (restPath, cliRelPath, 'xmlspec'),
                 cliGetXMLSpecHandlerName])
            logger.debug('Created REST endpoints for %s', cliRelPath)

    return restResource
