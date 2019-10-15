import os
import json
import six
import sys

from girder.api.rest import Resource, boundHandler, \
    setResponseHeader, setRawResponse
from girder.api import access
from girder import logger
from girder.api.describe import Description, describeRoute

from .cli_utils import as_model, generate_description, \
    get_cli_parameters, return_parameter_file_name
from .prepare_task import prepare_task
from .direct_docker_run import run


_return_parameter_file_desc = """
    Filename in which to write simple return parameters
    (integer, float, integer-vector, etc.) as opposed to bulk
    return parameters (image, file, directory, geometry,
    transform, measurement, table).
"""


def _getParamDefaultVal(param):
    if param.default is not None:
        return json.dumps(param.default)
    elif param.typ == 'boolean':
        return json.dumps(False)
    elif param.isVector():
        return json.dumps(None)
    elif param.isExternalType():
        return None
    else:
        raise Exception(
            'optional parameters of type %s must '
            'provide a default value in the xml' % param.typ)


def _addInputParamToHandler(param, handlerDesc, required=True):
    # add to route description
    desc = param.description

    if param.isExternalType():
        desc = 'Girder ID of input %s - %s: %s' \
                    % (param.typ, param.identifier(), param.description)

    handlerDesc.param(param.identifier(), desc, dataType='string',
                      default=_getParamDefaultVal(param) if not required else None,
                      required=required)


def _addOutputParamToHandler(param, handlerDesc, required=True):
    if not param.isExternalType():  # just files are supported
        return

    # add param for parent folder to route description
    handlerDesc.param(param.identifier() + '_folder',
                      'Girder ID of parent folder '
                      'for output %s - %s: %s'
                      % (param.typ, param.typ, param.description),
                      dataType='string', required=required)

    # add param for name of current output to route description
    handlerDesc.param(param.identifier(),
                      'Name of output %s - %s: %s'
                      % (param.typ, param.identifier(), param.description),
                      dataType='string', required=required)


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
        token = self.getCurrentToken()
        jobTitle = '.'.join((restResource.resourceName, cliName))

        container_args = [cliRelPath]
        container_args.extend(prepare_task(params, user, token, index_params, opt_params, has_simple_return_file))

        job = run.delay(
            girder_job_title=jobTitle,
            image=dockerImage, pull_image=False,
            container_args=container_args
        )
        return job.job

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
