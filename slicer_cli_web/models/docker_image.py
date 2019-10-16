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

from girder.constants import AccessType
from girder.models.folder import Folder
from girder.models.item import Item


def _split(name):
    if ':' in name:
        return name.split(':')
    return name.split('@')


class CLIItem(object):
    def __init__(self, item):
        self.item = item
        self._id = item['_id']
        self.name = item['name']
        desc = item['meta']
        self.type = desc['type']
        self.xml = desc['xml']
        if isinstance(self.xml, six.text_type):
            self.xml = self.xml.encode('utf8')

    @staticmethod
    def find(itemId, user):
        itemModel = Item()
        item = itemModel.load(itemId, user=user, level=AccessType.READ)
        if not item:
            return None
        return CLIItem(item)


class DockerImageItem(object):
    def __init__(self, imageFolder, tagFolder, user):
        self.image = imageFolder['name']
        self.tag = tagFolder['name']
        self.name = '%s:%s' % (self.image, self.tag)
        self.imageFolder = imageFolder
        self.tagFolder = tagFolder
        self._id = self.tagFolder['_id']
        self.user = user

        self.restPath = self.name.replace(':', '_').replace('/', '_').replace('@', '_')

    def getCLIs(self):
        itemModel = Item()
        q = {
            'meta.slicerCLIType': 'task',
            'folderId': self.tagFolder['_id']
        }
        if self.user:
            items = itemModel.findWithPermissions(q, user=self.user, level=AccessType.READ)
        else:
            items = itemModel.find(q)

        return [CLIItem(item) for item in items]

    @staticmethod
    def find(tagFolderId, user):
        folderModel = Folder()
        tagFolder = folderModel.load(tagFolderId, user=user, level=AccessType.READ)
        if not tagFolder:
            return None
        imageFolder = folderModel.load(tagFolder['parentId'], user=user, level=AccessType.READ)
        return DockerImageItem(imageFolder, tagFolder, user)

    @staticmethod
    def findAllImages(user=None, baseFolder=None):
        folderModel = Folder()
        q = {'meta.slicerCLIType': 'image'}
        if baseFolder:
            q['parentId'] = baseFolder['_id']

        if user:
            imageFolders = folderModel.findWithPermissions(q, user=user, level=AccessType.READ)
        else:
            imageFolders = folderModel.find(q)

        images = []

        for imageFolder in imageFolders:
            qt = {
                'meta.slicerCLIType': 'tag',
                'parentId': imageFolder['_id']
            }
            if user:
                tagFolders = folderModel.findWithPermissions(qt, user=user, level=AccessType.READ)
            else:
                tagFolders = folderModel.find(qt)
            for tagFolder in tagFolders:
                images.append(DockerImageItem(imageFolder, tagFolder, user))
        return images

    @staticmethod
    def removeImages(names, user):
        folderModel = Folder()
        removed = []
        for name in names:
            image, tag = _split(name)
            q = {
                'meta.slicerCLIType': 'image',
                'name': image
            }
            imageFolder = folderModel.findOne(q, user=user, level=AccessType.READ)
            if not imageFolder:
                continue
            qt = {
                'meta.slicerCLIType': 'tag',
                'parentId': imageFolder['_id'],
                'name': tag
            }
            tagFolder = folderModel.findOne(qt, user=user, level=AccessType.WRITE)
            if not tagFolder:
                continue
            folderModel.remove(tagFolder)
            removed.append(name)

            if folderModel.hasAccess(imageFolder, user, AccessType.WRITE) and folderModel.countFolders(imageFolder) == 0:
                # clean also empty image folders
                folderModel.remove(imageFolder)

        return removed

    @staticmethod
    def saveImage(name, cli_dict, user, baseFolder):
        """
        :param baseFolder
        :type Folder
        """
        folderModel = Folder()
        itemModel = Item()
        imageName, tagName = _split(name)

        image = folderModel.createFolder(baseFolder, imageName, 'Slicer CLI generated docker image folder',
                                         creator=user, reuseExisting=True)
        folderModel.setMetadata(image, dict(slicerCLIType='image'))

        tag = folderModel.createFolder(image, tagName, 'Slicer CLI generated docker image tag folder',
                                       creator=user, reuseExisting=True)
        folderModel.setMetadata(tag, dict(slicerCLIType='tag'))
        folderModel.clean(tag)

        for cli, desc in six.iteritems(cli_dict):
            item = itemModel.createItem(cli, user, tag, 'Slicer CLI generated CLI command item', reuseExisting=True)
            itemModel.setMetadata(item, dict(slicerCLIType='task'))
            itemModel.setMetadata(item, desc)

        return DockerImageItem(image, tag, user)

    @staticmethod
    def prepare():
        Item().ensureIndex(['meta.slicerCLIType', {'sparse': True}])
        Item().ensureIndex(['meta.slicerCLIType', {'sparse': True}])
