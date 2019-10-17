import os
import sys

from girder.api.rest import Resource, boundHandler, \
    setResponseHeader, setRawResponse, RestException
from girder.api import access
from girder import logger
from girder.api.describe import Description, describeRoute

from .cli_utils import as_model, generate_description, \
    get_cli_parameters, return_parameter_file_name
from .prepare_task import prepare_task, OPENAPI_DIRECT_TYPES, FOLDER_SUFFIX
from .girder_worker_plugin.direct_docker_run import run
from .models import CLIItem


_return_parameter_file_desc = """
    Filename in which to write simple return parameters
    (integer, float, integer-vector, etc.) as opposed to bulk
    return parameters (image, file, directory, geometry,
    transform, measurement, table).
"""


def _getParamDefaultVal(param):
    if param.default is not None:
        return param.default
    elif param.typ == 'boolean':
        return False
    elif param.isVector():
        return None
    elif param.isExternalType():
        return None
    else:
        raise Exception(
            'optional parameters of type %s must '
            'provide a default value in the xml' % param.typ)


def _addInputParamToHandler(param, handlerDesc, required=True):
    # add to route description
    desc = param.description
    dataType = 'string'
    enum = None
    schema = None

    if param.isExternalType():
        desc = 'Girder ID of input %s - %s: %s' \
                    % (param.typ, param.identifier(), param.description)
    elif param.typ in OPENAPI_DIRECT_TYPES:
        dataType = param.typ
    elif param.typ == 'string-enumeration':
        enum = param.elements
    elif param.isVector():
        dataType = 'json'
        itemType = param.typ
        if param.typ == 'float' or param.typ == 'double':
            itemType = 'number'
        schema = dict(type='array', items=dict(type=itemType))
    else:
        dataType = 'json'
        desc = '%s as JSON (%s)' % (param.description, param.typ)

    defaultValue = None
    if not required or param.default is not None:
        defaultValue = _getParamDefaultVal(param)

    if dataType == 'json':
        handlerDesc.jsonParam(param.identifier(), desc,
                              default=defaultValue,
                              required=required, schema=schema)
    else:
        handlerDesc.param(param.identifier(), desc, dataType=dataType, enum=enum,
                          default=defaultValue,
                          required=required)


def _addOutputParamToHandler(param, handlerDesc, required=True):
    if not param.isExternalType():  # just files are supported
        return

    # add param for parent folder to route description
    handlerDesc.param(param.identifier() + FOLDER_SUFFIX,
                      'Girder ID of parent folder '
                      'for output %s - %s: %s'
                      % (param.typ, param.typ, param.description),
                      dataType='string', required=required)

    # add param for name of current output to route description

    defaultName = None
    try:
        defaultName = '%s%s' % (param.identifier(), param.defaultExtension())
    except KeyError:
        pass

    handlerDesc.param(param.identifier(),
                      'Name of output %s - %s: %s'
                      % (param.typ, param.identifier(), param.description),
                      default=defaultName,
                      dataType='string', required=required)


def _addReturnParameterFileParamToHandler(handlerDesc):

    curName = return_parameter_file_name
    curType = 'file'
    curDesc = _return_parameter_file_desc

    # add param for parent folder to route description
    handlerDesc.param(curName + FOLDER_SUFFIX,
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


def genHandlerToRunDockerCLI(dockerImage, cliItem, restResource):
    """Generates a handler to run docker CLI using girder_worker

    Parameters
    ----------
    dockerImage : str
        Docker image in which the CLI resides
    cliItem : CLIItem
    restResource : girder.api.rest.Resource
        The object of a class derived from girder.api.rest.Resource to which
        this handler will be attached

    Returns
    -------
    function
        Returns a function that runs the CLI using girder_worker

    """

    cliName = os.path.normpath(cliItem.name).replace(os.sep, '.')
    itemId = cliItem._id

    clim = as_model(cliItem.xml)

    # do stuff needed to create REST endpoint for cLI
    handlerDesc = Description(clim.title).notes(generate_description(clim))

    # get CLI parameters
    index_params, opt_params, simple_out_params = get_cli_parameters(clim)

    for param in index_params:
        if param.channel == 'output':
            _addOutputParamToHandler(param, handlerDesc, True)
        else:
            _addInputParamToHandler(param, handlerDesc, True)
    for param in opt_params:
        if param.channel == 'output':
            _addOutputParamToHandler(param, handlerDesc, False)
        else:
            _addInputParamToHandler(param, handlerDesc, False)

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
        currentItem = CLIItem.find(itemId, user)
        if not currentItem:
            raise RestException('Invalid CLI Item id (%s).' % (itemId))
        token = self.getCurrentToken()
        jobTitle = '.'.join((restResource.resourceName, cliName))

        container_args = [currentItem.name]
        args, result_hooks = prepare_task(params, user, token, index_params, opt_params, has_simple_return_file)
        container_args.extend(args)

        job = run.delay(
            girder_user=user,
            girder_job_type='Slicer CLI Task',
            girder_job_title=jobTitle,
            girder_result_hooks=result_hooks,
            image=dockerImage, pull_image=False,
            container_args=container_args
        )
        return job.job

    return cliHandler


def genHandlerToGetDockerCLIXmlSpec(itemId, name, restResource):
    """Generates a handler that returns the XML spec of the docker CLI

    Parameters
    ----------
    itemId : str
        Girder Item Id
    name : str
        Relative path of the CLI which is needed to run the CLI by running
        the command docker run `dockerImage` `name`
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

    # define the handler that returns the CLI's xml spec
    @boundHandler(restResource)
    @access.user
    @describeRoute(
        Description('Get XML spec of %s CLI' % name)
    )
    def getXMLSpecHandler(self, *args, **kwargs):
        item = CLIItem.find(itemId, self.getCurrentUser())
        if not item:
            raise RestException('Invalid CLI Item id (%s).' % (itemId))
        setResponseHeader('Content-Type', 'application/xml')
        setRawResponse()
        return item.xml

    return getXMLSpecHandler


def genRESTEndPointsForSlicerCLIsForImage(restResource, docker_image):
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
    docker_image : DockerImageItem

    """

    # validate restResource argument
    if not isinstance(restResource, Resource):
        raise Exception('restResource must be a Docker Resource')

    dimg = docker_image.name
    restPath = docker_image.restPath

    # Add REST end-point for each CLI
    for cli in docker_image.getCLIs():
        # create a POST REST route that runs the CLI
        try:
            cliRunHandler = genHandlerToRunDockerCLI(
                dimg, cli, restResource)
        except Exception:
            logger.exception('Failed to create REST endpoints for %r',
                             cli.name)
            continue

        cliSuffix = os.path.normpath(cli.name).replace(os.sep, '_')

        cliRunHandlerName = restPath+'_run_' + cliSuffix
        setattr(restResource, cliRunHandlerName, cliRunHandler)
        restResource.route('POST',
                           (restPath, cli.name, 'run'),
                           getattr(restResource, cliRunHandlerName))

        # store new rest endpoint
        restResource.storeEndpoints(
            dimg, cli.name, 'run', ['POST', (restPath, cli.name, 'run'),
                                    cliRunHandlerName])

        # create GET REST route that returns the xml of the CLI
        try:
            cliGetXMLSpecHandler = genHandlerToGetDockerCLIXmlSpec(
                cli._id, cli.name,
                restResource)
        except Exception:
            logger.exception('Failed to create REST endpoints for %s',
                             cli.name)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error('%r', [exc_type, fname, exc_tb.tb_lineno])
            continue

        cliGetXMLSpecHandlerName = restPath+'_get_xml_' + cliSuffix
        setattr(restResource,
                cliGetXMLSpecHandlerName,
                cliGetXMLSpecHandler)
        restResource.route('GET',
                           (restPath, cli.name, 'xmlspec',),
                           getattr(restResource, cliGetXMLSpecHandlerName))

        restResource.storeEndpoints(
            dimg, cli.name, 'xmlspec',
            ['GET', (restPath, cli.name, 'xmlspec'),
                cliGetXMLSpecHandlerName])
        logger.debug('Created REST endpoints for %s', cli.name)

    return restResource
