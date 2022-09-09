#############################################################################
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
#############################################################################


import json
import os
import re

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute, describeRoute
from girder.api.rest import setRawResponse, setResponseHeader
from girder.api.v1.resource import Resource, RestException
from girder.constants import AccessType, SortDir
from girder.exceptions import AccessException
from girder.models.item import Item
from girder.utility import path as path_util
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import setResponseTimeLimit
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from .config import PluginSettings
from .models import CLIItem, DockerImageItem, DockerImageNotFoundError
from .rest_slicer_cli import genRESTEndPointsForSlicerCLIsForItem


class DockerResource(Resource):
    """
    Resource object that handles runtime generation and deletion of rest
    endpoints
    """

    jobType = 'slicer_cli_web_job'

    def __init__(self, name):
        super().__init__()
        self.currentEndpoints = {}
        self.resourceName = name
        self.jobType = 'slicer_cli_web_job'
        self.route('PUT', ('docker_image',), self.setImages)
        self.route('DELETE', ('docker_image',), self.deleteImage)
        self.route('GET', ('docker_image',), self.getDockerImages)

        self.route('GET', ('cli',), self.getItems)
        self.route('GET', ('cli', ':id',), self.getItem)
        self.route('DELETE', ('cli', ':id',), self.deleteItem)
        # run is generated per item for better validation
        self.route('GET', ('cli', ':id', 'xml'), self.getItemXML)

        self.route('GET', ('path_match', ), self.getMatchingResource)

        self._generateAllItemEndPoints()

    @access.public
    @describeRoute(
        Description('List docker images and their CLIs')
        .notes('You must be logged in to see any results.')
    )
    def getDockerImages(self, params):
        data = {}
        if self.getCurrentUser():
            for image in DockerImageItem.findAllImages(self.getCurrentUser()):
                imgData = {}
                for cli in image.getCLIs():
                    basePath = '/%s/cli/%s' % (self.resourceName, cli._id)
                    imgData[cli.name] = {
                        'type': cli.type,
                        'xmlspec': basePath + '/xml',
                        'run': basePath + '/run'
                    }
                data.setdefault(image.image, {})[image.tag] = imgData
        return data

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
        job = Job().createLocalJob(
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

        Job().scheduleJob(job)

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
        if isinstance(param, bytes):
            param = param.decode('utf8')
        if isinstance(param, str):
            try:
                nameList = json.loads(param)
            except ValueError:
                pass
        if isinstance(nameList, str):
            nameList = [nameList]
        if not isinstance(nameList, list):
            raise RestException('A valid string or a list of strings is required.')
        for img in nameList:
            if not isinstance(img, str):
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
                    level=AccessType.WRITE, required=False)
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
        job = Job().createLocalJob(
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
        Job().scheduleJob(job)
        return job

    def storeEndpoints(self, imgName, cliName, undoFunction):
        """
        Information on each rest endpoint is saved so they can be
        deleted when docker images are removed or loaded.

        :param imgName: The full name of the docker image with the tag.
            This name must match exactly with the name the command
            docker images displays in the console
        :type imgName: string
        :param cliName: The name of the cli whose rest endpoint is being stored. The
            cli must match exactly with what the docker image returns when
            running <docker image> --list_cli
        :type cliName: string
        """
        img = self.currentEndpoints.setdefault(imgName, {})
        img[cliName] = undoFunction

    def deleteImageEndpoints(self, imageList=None):

        if imageList is None:
            imageList = self.currentEndpoints.keys()
        for imageName in list(imageList):
            for undoFunction in self.currentEndpoints.pop(imageName, {}).values():
                undoFunction()

    def _generateAllItemEndPoints(self):
        # sort by name and creation date desc
        items = sorted(CLIItem.findAllItems(), key=lambda x: (x.restPath, x.item['created']),
                       reverse=True)

        seen = set()
        for item in items:
            # default if not seen yet
            genRESTEndPointsForSlicerCLIsForItem(self, item, item.restPath not in seen)
            seen.add(item.restPath)

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
            self.deleteImageEndpoints()
            self._generateAllItemEndPoints()

    def _dump(self, item, details=False):
        r = {
            '_id': item._id,
            'name': item.name,
            'type': item.type,
            'image': item.image,
            'description': item.item['description']
        }
        if details:
            r['xml'] = item.item['meta']['xml']
        return r

    @access.user
    @autoDescribeRoute(
        Description('List CLIs')
        .errorResponse('You are not logged in.', 403)
        .modelParam('folder', 'The base folder to look for tasks', 'folder', paramType='query',
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
        return self._dump(CLIItem(item), True)

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

    @access.public
    @autoDescribeRoute(
        Description(
            'Get the most recently updated resource that has a name and path '
            'that matches a regular expression')
        .notes('This can be very slow if name is too general.')
        .param('name', 'A regular expression to match the name of the '
               'resource.', required=False)
        .param('path', 'A regular expression to match the entire resource path.', required=False)
        .param('relative_path', 'A relative resource path to the base item.', required=False)
        .param('base_id', 'The base girder id for the relative path', required=False)
        .param('base_type', 'The base girder type for the relative path', required=False)
        .param('type', 'The type of the resource (item, file, etc.).')
        .errorResponse('Invalid resource type.')
        .errorResponse('No matches.')
    )
    def getMatchingResource(self, name, path, type, relative_path, base_id, base_type):
        setResponseTimeLimit(86400)
        user = self.getCurrentUser()
        model = ModelImporter.model(type)
        pattern = None
        if path:
            pattern = re.compile(path)
        if relative_path:
            if not base_id or not base_type:
                raise RestException('No matches.')
            try:
                base_model = ModelImporter.model(base_type).load(base_id, user=user)
                base_path = path_util.getResourcePath(base_type, base_model, user=user)
                new_path = os.path.normpath(os.path.join(base_path, relative_path))
                doc = path_util.lookUpPath(new_path, user=user)['document']
                doc['_path'] = new_path.split('/')[2:]
                if type == 'folder':
                    doc['_path'] = doc['_path'][:-1]
            except Exception:
                raise RestException('No matches.')
            if not name and not path:
                return doc
            pattern = re.compile('(?=^' + re.escape(new_path) + ').*' + (path or ''))
        for doc in model.findWithPermissions(
                {'name': {'$regex': name}} if name else {},
                sort=[('updated', SortDir.DESCENDING), ('created', SortDir.DESCENDING)],
                user=user, level=AccessType.READ):
            try:
                resourcePath = path_util.getResourcePath(type, doc, user=user)
                if not pattern or pattern.search(resourcePath):
                    doc['_path'] = resourcePath.split('/')[2:]
                    if type == 'folder':
                        doc['_path'] = doc['_path'][:-1]
                    return doc
            except (AccessException, TypeError):
                pass
        raise RestException('No matches.')
