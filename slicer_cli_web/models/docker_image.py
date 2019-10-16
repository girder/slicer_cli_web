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
    def __init__(self, folder, user):
        self.name = folder['name']
        self.folder = folder
        self._id = self.folder['_id']
        self.user = user

        if ':' in self.name:
            imageAndTag = self.name.split(':')
        else:
            imageAndTag = self.name.split('@')
        self.image = imageAndTag[0]
        self.tag = imageAndTag[1]
        self.restPath = self.name.replace(':', '_').replace('/', '_').replace('@', '_')

    def getCLIs(self):
        itemModel = Item()
        q = {
            'meta.isSlicerCLITask': True,
            'folderId': self.folder['_id']
        }
        if self.user:
            items = itemModel.findWithPermissions(q, user=self.user, level=AccessType.READ)
        else:
            items = itemModel.find(q)

        return [CLIItem(item) for item in items]

    @staticmethod
    def find(folderId, user):
        folderModel = Folder()
        folder = folderModel.load(folderId, user=user, level=AccessType.READ)
        if not folder:
            return None
        return DockerImageItem(folder, user)

    @staticmethod
    def findAllImages(user=None, baseFolder=None):
        folderModel = Folder()
        q = {'meta.isSlicerCLIImage': True}
        if baseFolder:
            q['parentId'] = baseFolder['_id']
        if user:
            folders = folderModel.findWithPermissions(q, user=user, level=AccessType.READ)
        else:
            folders = folderModel.find(q)
        return [DockerImageItem(folder, user) for folder in folders]

    @staticmethod
    def removeImages(names, user):
        folderModel = Folder()
        q = {
            'meta.isSlicerCLIImage': True,
            'name': {'$in': names}
        }
        folders = list(folderModel.find(q, user=user, level=AccessType.WRITE))
        for folder in folders:
            folderModel.remove(folder)
        return [folder['name'] for folder in folders]

    @staticmethod
    def saveImage(name, cli_dict, user, baseFolder):
        """
        :param baseFolder
        :type Folder
        """
        folderModel = Folder()
        itemModel = Item()

        image = folderModel.createFolder(baseFolder, name, 'Slicer CLI generated docker image folder',
                                         creator=user, reuseExisting=True)
        folderModel.setMetadata(image, dict(isSlicerCLIImage=True))

        folderModel.clean(image)

        for cli, desc in six.iteritems(cli_dict):
            item = itemModel.createItem(cli, user, image, 'Slicer CLI generated CLI command item', reuseExisting=True)
            item.setMetadata(image, dict(isSlicerCLITask=True))
            item.setMetadata(image, desc)

        return DockerImageItem(image, user)

    @staticmethod
    def prepare():
        Folder().ensureIndex(['meta.isSlicerCLIImage', {'sparse': True}])
        Item().ensureIndex(['meta.isSlicerCLITask', {'sparse': True}])
