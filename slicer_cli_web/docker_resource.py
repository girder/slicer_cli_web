# !/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################


import six
import json

from girder.api.v1.resource import Resource, RestException
from girder import logger

from girder.api.rest import \
    setResponseHeader, setRawResponse
from girder.api import access
from girder.constants import AccessType
from girder.api.describe import autoDescribeRoute, Description, describeRoute
from girder.utility.model_importer import ModelImporter
from girder.models.item import Item
from .rest_slicer_cli import genRESTEndPointsForSlicerCLIsForImage
from girder_jobs.constants import JobStatus

from .models import DockerImageNotFoundError, DockerImageItem, CLIItem
from .config import PluginSettings


class DockerResource(Resource):
    """
    Resource object that handles runtime generation and deletion of rest
    endpoints
    """

    jobType = 'slicer_cli_web_job'

    def __init__(self, name):
        super(DockerResource, self).__init__()
        self.currentEndpoints = {}
        self.resourceName = name
        self.jobType = 'slicer_cli_web_job'
        self.route('PUT', (name, 'docker_image'), self.setImages)
        self.route('DELETE', (name, 'docker_image'), self.deleteImage)
        self.route('GET', (name, 'docker_image'), self.getDockerImages)

        self.route('GET', (name, 'cli'), self.getItems)
        self.route('GET', (name, 'cli', ':id',), self.getItem)
        self.route('DELETE', (name, 'cli', ':id',), self.deleteItem)
        self.route('GET', (name, 'cli', ':id', 'xml'), self.getItemXML)

    @access.user
    @describeRoute(
        Description('List docker images and their CLIs')
        .errorResponse('You are not logged in.', 403)
    )
    def getDockerImages(self, params):
        data = {}
        for image in DockerImageItem.findAllImages(self.getCurrentUser()):
            name, tag, imgData = self.createRestDataForImageVersion(image)
            data.setdefault(name, {})[tag] = imgData
        return data

    def createRestDataForImageVersion(self, dockerImage):
        """
        Creates a dictionary with rest endpoint information for the given
        DockerImage object

        :param dockerImage: DockerImage object
        :type dockerImage: DockerImageItem

        :returns: structured dictionary documenting clis and rest
            endpoints for this image version
        """

        name = dockerImage.name
        endpointData = self.currentEndpoints.setdefault(name, {})

        userAndRepo = dockerImage.image
        tag = dockerImage.tag

        data = {}

        for cli in dockerImage.getCLIs():
            if cli.name not in endpointData:
                logger.warning('"%s" not present in endpoint data.' % cli.name)
                continue
            data[cli.name] = {}

            data[cli.name]['type'] = cli.type
            cli_endpoints = endpointData[cli.name]

            for (operation, endpointRoute) in six.iteritems(cli_endpoints):
                cli_list = endpointRoute[1]
                if cli.name in cli_list:
                    data[cli.name][operation] = '/' + self.resourceName + \
                                                '/' + '/'.join(cli_list)
        return userAndRepo, tag, data

    @access.admin
    @describeRoute(
        Description('Remove a docker image')
        .notes('Must be a system administrator to call this.')
        .param('name', 'The name or a list of names of the docker images to be '
               'removed', required=True)
        .param('delete_from_local_repo',
               'If True the image is deleted from the local repo, requiring '
               'it to be pulled from a remote repository the next time it is '
               'used.  If False the metadata regarding the image is deleted, '
               'but the docker image remains.', required=False,
               dataType='boolean', default=False)
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('Failed to set system setting.', 500)
    )
    def deleteImage(self, params):
        self.requireParams(('name',), params)
        if 'delete_from_local_repo' in params:
            deleteImage = str(params['delete_from_local_repo']).lower() == 'true'
        else:
            deleteImage = False
        nameList = self.parseImageNameList(params['name'])
        self._deleteImage(nameList, deleteImage)

    def _deleteImage(self, names, deleteImage):
        """
        Removes the docker images and there respective clis endpoints

        :param names: The name of the docker image (user/rep:tag)
        :type name: list
        :param deleteImage: Boolean indicating whether to delete the docker
            image from the local machine.(if True this is equivalent to
            docker rmi -f <image> )
        :type name: boolean
        """
        removed = DockerImageItem.removeImages(names, self.getCurrentUser())
        if removed != names:
            rest = [name for name in names if name not in removed]
            raise RestException('Some docker images could not be removed. %s' % (rest))
        self.deleteImageEndpoints(removed)

        try:
            if deleteImage:
                self._deleteDockerImages(removed)
        except DockerImageNotFoundError as err:
            raise RestException('Invalid docker image name. ' + str(err))

    def _deleteDockerImages(self, removed):
        """
        Creates an asynchronous job to delete the docker images listed in name
        from the local machine
        :param removed:A list of docker image names
        :type removed: list of strings
        """
        jobModel = ModelImporter.model('job', 'jobs')

        job = jobModel.createLocalJob(
            module='slicer_cli_web.image_job',

            function='deleteImage',
            kwargs={
                'deleteList': removed
            },
            title='Deleting Docker Images',
            user=self.getCurrentUser(),
            type=self.jobType,
            public=True,
            asynchronous=True
        )

        jobModel.scheduleJob(job)

    def parseImageNameList(self, param):
        """
        Parse a string to get a list of image names.  If the string is a JSON
        list of strings or a JSON string (with quotes), it is processed as
        JSON.  Otherwise, the input value is treated as a single image name.

        :param param: a parameter with an image name, a JSON image name, or a
            JSON list of image names.
        :returns: a list of image names.
        """
        nameList = param
        if isinstance(param, six.binary_type):
            param = param.decode('utf8')
        if isinstance(param, six.string_types):
            try:
                nameList = json.loads(param)
            except ValueError:
                pass
        if isinstance(nameList, six.string_types):
            nameList = [nameList]
        if not isinstance(nameList, list):
            raise RestException('A valid string or a list of strings is required.')
        for img in nameList:
            if not isinstance(img, six.string_types):
                raise RestException('%r is not a valid string.' % img)
            if ':' not in img and '@' not in img:
                raise RestException('Image %s does not have a tag or digest' % img)
        return nameList

    @access.admin
    @describeRoute(
        Description('Add one or a list of images')
        .notes('Must be a system administrator to call this.')
        .param('name', 'A name or a list of names of the docker images to be '
               'loaded', required=True)
        .modelParam('folder', 'The base folder to upload the tasks to', 'folder', paramType='query',
                    level=AccessType.WRITE, required=not PluginSettings.has_task_folder())
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('Failed to set system setting.', 500)
    )
    def setImages(self, params):
        """
        Validates the new images to be added (if they exist or not) and then
        attempts to collect xml data to be cached. a job is then called to
        update the girder collection containing the cached docker image data
        """
        self.requireParams(('name',), params)
        nameList = self.parseImageNameList(params['name'])
        folder = params.get('folder', PluginSettings.get_task_folder())
        if not folder:
            raise RestException('no upload folder given or defined by default')
        return self._createPutImageJob(nameList, folder)

    def _createPutImageJob(self, nameList, baseFolder):
        jobModel = ModelImporter.model('job', 'jobs')
        job = jobModel.createLocalJob(
            module='slicer_cli_web.image_job',
            function='jobPullAndLoad',
            kwargs={
                'nameList': nameList,
                'folder': baseFolder['_id'] if isinstance(baseFolder, dict) else baseFolder
            },
            title='Pulling and caching docker images',
            type=self.jobType,
            user=self.getCurrentUser(),
            public=True,
            asynchronous=True
        )
        jobModel.scheduleJob(job)
        return job

    def storeEndpoints(self, imgName, cli, operation, argList):
        """
        Information on each rest endpoint is saved so they can be
        deleted when docker images are removed or loaded.

        :param imgName: The full name of the docker image with the tag.
            This name must match exactly with the name the command
            docker images displays in the console
        :type imgName: string
        :param cli: The name of the cli whose rest endpoint is being stored. The
            cli must match exactly with what teh docker image returns when
            running <docker image> --list_cli
        :type cli: string
        :param operation: The action the rest endpoint will execute run or
            xmlspec
        :type operation: string
        :argList:list of details for a specific endpoint. The arglist should
            contain [method,route_tuple,endpoint_method_handler_name].  The
            route tuple should consist of the docker image name, the cli name
            and the operation. Since this tuple forms the rest route, the exact
            docker image name may not be used due to ':' used in docker image
            names. As a result the docker name and cli name used in the rest
            route do not have to match the actual docker name and cli name
        """
        if imgName in self.currentEndpoints:
            if cli in self.currentEndpoints[imgName]:
                self.currentEndpoints[imgName][cli][operation] = argList
            else:
                self.currentEndpoints[imgName][cli] = {}
                self.currentEndpoints[imgName][cli][operation] = argList

        else:
            self.currentEndpoints[imgName] = {}
            self.currentEndpoints[imgName][cli] = {}
            self.currentEndpoints[imgName][cli][operation] = argList

    def deleteImageEndpoints(self, imageList=None):

        if imageList is None:
            imageList = six.iterkeys(self.currentEndpoints)
        for imageName in list(imageList):
            if imageName in self.currentEndpoints:
                for val in six.itervalues(
                        self.currentEndpoints[imageName]):
                    for endpoint in six.itervalues(val):
                        try:
                            self.removeRoute(endpoint[0], endpoint[1],
                                             getattr(self, endpoint[2]))
                            delattr(self, endpoint[2])
                        except Exception:
                            logger.exception('Failed to remove route')
            del self.currentEndpoints[imageName]

    def addRestEndpoints(self, event):
        """
        Determines if the job event being triggered is due to the caching of
        new docker images or deleting a docker image off the local machine.  If
        a new image is being loaded all old rest endpoints are deleted and
        endpoints for all cached docker images are regenerated.

        :param event: An event dictionary
        """
        job = event.info['job']

        if job['type'] == self.jobType and job['status'] == JobStatus.SUCCESS:
            images = DockerImageItem.findAllImages()
            self.deleteImageEndpoints()
            for image in images:
                genRESTEndPointsForSlicerCLIsForImage(self, image)

    def _dump(self, item, short=True):
        r = {
            '_id': item._id,
            'name': item.name,
            'type': item.type,
            'description': item.item['description']
        }
        if short:
            return r

        r['xml'] = item.item['meta']['xml']
        return r

    @access.user
    @autoDescribeRoute(
        Description('List CLIs')
        .errorResponse('You are not logged in.', 403)
        .modelParam('folder', 'The base folder to upload the tasks to', 'folder', paramType='query',
                    level=AccessType.WRITE, required=False)
    )
    def getItems(self, folder):
        items = CLIItem.findAllItems(self.getCurrentUser(), baseFolder=folder)
        return [self._dump(item) for item in items]

    @access.user
    @autoDescribeRoute(
        Description('Get a specific CLI')
        .errorResponse('You are not logged in.', 403)
        .modelParam('id', 'The task item', 'item',
                    level=AccessType.READ)
    )
    def getItem(self, item):
        return self._dump(CLIItem(item), False)

    @access.user
    @autoDescribeRoute(
        Description('Get a specific CLI')
        .errorResponse('You are not logged in.', 403)
        .modelParam('id', 'The task item', 'item',
                    level=AccessType.WRITE)
    )
    def deleteItem(self, item):
        Item().remove(item)
        return dict(status='OK')

    @access.user
    @autoDescribeRoute(
        Description('Get a specific CLI')
        .errorResponse('You are not logged in.', 403)
        .modelParam('id', 'The task item', 'item',
                    level=AccessType.READ)
    )
    def getItemXML(self, item):
        setResponseHeader('Content-Type', 'application/xml')
        setRawResponse()
        return CLIItem(item).xml
