from girder.api.rest import Resource, boundHandler, \
    RestException
from girder.api import access
from girder import logger
from girder.api.describe import Description, describeRoute

from .cli_utils import as_model, generate_description, \
    get_cli_parameters, return_parameter_file_name
from .prepare_task import prepare_task, OPENAPI_DIRECT_TYPES, FOLDER_SUFFIX
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
    elif param.typ == 'float' or param.typ == 'integer':
        return 0
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
        desc = 'Girder ID of input %s - %s: %s' % (param.typ, param.identifier(), param.description)
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
        desc = '%s as JSON (%s)' % (param.description, param.typ)
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

    defaultFileExtension = None
    try:
        defaultFileExtension = param.defaultExtension()
    except KeyError:  # file is not an EXTERNAL_TYPE in the parser
        if param.fileExtensions:
            defaultFileExtension = param.fileExtensions[0]

    if defaultFileExtension and '|' in defaultFileExtension:
        defaultFileExtension = defaultFileExtension.split('|')[0]

    defaultValue = ('%s%s' % (param.identifier(), defaultFileExtension)
                    if defaultFileExtension else None)
    handlerDesc.param(param.identifier(),
                      'Name of output %s - %s: %s'
                      % (param.typ, param.identifier(), param.description),
                      default=defaultValue,
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


def genHandlerToRunDockerCLI(cliItem):
    """Generates a handler to run docker CLI using girder_worker

    Parameters
    ----------
    cliItem : CLIItem

    Returns
    -------
    function
        Returns a function that runs the CLI using girder_worker

    """

    itemId = cliItem._id

    clim = as_model(cliItem.xml)
    cliTitle = clim.title

    # do stuff needed to create REST endpoint for cLI
    handlerDesc = Description(clim.title) \
        .notes(generate_description(clim)) \
        .produces('application/json')

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

    @access.user
    @describeRoute(handlerDesc)
    def cliHandler(resource, params):
        from .girder_worker_plugin.direct_docker_run import run

        user = resource.getCurrentUser()
        currentItem = CLIItem.find(itemId, user)
        if not currentItem:
            raise RestException('Invalid CLI Item id (%s).' % (itemId))
        token = resource.getCurrentToken()

        container_args = [currentItem.name]
        reference = {'slicer_cli_web': {
            'title': cliTitle,
            'image': currentItem.image,
            'name': currentItem.name,
        }}
        args, result_hooks, primary_input_name = prepare_task(
            params, user, token, index_params, opt_params,
            has_simple_return_file, reference)
        container_args.extend(args)

        jobType = '%s#%s' % (currentItem.image, currentItem.name)

        if primary_input_name:
            jobTitle = '%s on %s' % (cliTitle, primary_input_name)
        else:
            jobTitle = cliTitle

        job = run.delay(
            girder_user=user,
            girder_job_type=jobType,
            girder_job_title=jobTitle,
            girder_result_hooks=result_hooks,
            image=currentItem.digest,
            pull_image='if-not-present',
            container_args=container_args
        )
        return job.job

    return cliHandler


def genRESTEndPointsForSlicerCLIsForItem(restResource, cliItem, registerNamedRoute=False):
    """Generates REST end points for slicer CLIs placed in subdirectories of a
    given root directory and attaches them to a REST resource with the given
    name.

    For each CLI, it creates:
    * a GET Route (<apiURL>/`restResourceName`/<cliRelativePath>/xml)
    that returns the xml spec of the CLI
    * a POST Route (<apiURL>/`restResourceName`/<cliRelativePath>/run)
    that runs the CLI

    It also creates a GET route (<apiURL>/`restResourceName`) that returns a
    list of relative routes to all CLIs attached to the generated REST resource

    Parameters
    ----------
    restResource : a dockerResource
        REST resource to which the end-points should be attached
    cliItem : CliItem

    """

    # validate restResource argument
    if not isinstance(restResource, Resource):
        raise Exception('restResource must be a Docker Resource')

    try:
        handler = genHandlerToRunDockerCLI(cliItem)

        # define CLI handler function
        cliRunHandler = boundHandler(restResource)(handler)

        cliRunHandlerName = 'run_%s' % cliItem._id
        setattr(restResource, cliRunHandlerName, cliRunHandler)

        restRunPath = ('cli', str(cliItem._id), 'run')
        restResource.route('POST', restRunPath, cliRunHandler)

        if registerNamedRoute:
            restNamedRunPath = (cliItem.restBasePath, cliItem.name, 'run')
            restResource.route('POST', restNamedRunPath, cliRunHandler)

        def undoFunction():
            try:
                restResource.removeRoute('POST', restRunPath, cliRunHandler)
                if registerNamedRoute:
                    restResource.removeRoute('POST', restNamedRunPath, cliRunHandler)
                delattr(restResource, cliRunHandlerName)
            except Exception:
                logger.exception('Failed to remove route')

        # store new rest endpoint
        restResource.storeEndpoints(cliItem.image, cliItem.name, undoFunction)

        logger.debug('Created REST endpoints for %s', cliItem.name)
    except Exception:
        logger.exception('Failed to create REST endpoints for %r',
                         cliItem.name)

    return restResource
