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

from girder.models.folder import Folder
from girder.models.item import Item


class CLIItem(object):
    def __init__(self, name, desc):
        self.name = name
        self.type = desc['type']
        self.xml = desc['xml']


class DockerImageItem(object):
    def __init__(self, name, cli_dict):
        self.name = name
        self.clis = [CLIItem(key, val) for key, val in six.iteritems(cli_dict)]

    @staticmethod
    def findAllImages():
        # remove all previous endpoints
        # dockermodel = ModelImporter.model('docker_image_model',
        #                                   'slicer_cli_web')
        # return dockermodel.loadAllImages()
        return []

    @staticmethod
    def removeImages(names):
        return []

    @staticmethod
    def deleteDockerImageFromRepo(names, jobType):
        return None

    @staticmethod
    def putImages(names, jobType, replace=False):
        return []

    @staticmethod
    def prepare():
        Folder().ensureIndex(['meta.isSlicerCLIImage', {'sparse': True}])
        Item().ensureIndex(['meta.isSlicerCLITask', {'sparse': True}])

    def getCLIs(self):
        return self.clis


# class DockerImage(object):
#     """
#     Represents docker image and contains metadata on a specific image
#     """
#     # keys used by the dictionary that stores metadata on the image
#     imageName = 'docker_image_name'
#     imageHash = 'imagehash'
#     type = 'type'
#     xml = 'xml'
#     cli_dict = 'cli_list'
#     # structure of the dictionary to store metadata
#     # {
#     #     'imagehash': <hash of docker image name>
#     #     'cli_list': {
#     #         <cli_name>: {
#     #             'type': <type>
#     #             'xml': <xml>
#     #         }
#     #     }
#     #     'docker_image_name': <name>
#     # }

#     def __init__(self, name, cli_dict):
#         # TODO
#         try:
#             if isinstance(name, six.string_types):
#                 imageKey = DockerImage.getHashKey(name)
#                 self.data = {}
#                 self.data[DockerImage.imageName] = name
#                 self.data[DockerImage.cli_dict] = {}
#                 self.data[DockerImage.imageHash] = imageKey
#                 self.hash = imageKey
#                 self.name = name
#                 # TODO check/validate schema of dict
#             elif isinstance(name, dict):
#                 jsonschema.validate(name, DockerImageStructure.ImageSchema)
#                 self.data = name.copy()
#                 self.name = self.data[DockerImage.imageName]
#                 self.hash = DockerImage.getHashKey(self.name)
#             else:
#                 raise DockerImageError(
#                     'Image should be a string, or dict could not add the image',
#                     'bad init val')
#         except Exception as err:
#             logger.exception('Could not initialize docker image %r', name)
#             raise DockerImageError(
#                 'Could not initialize instance of Docker Image \n' + str(err))

#     def addCLI(self, cli_name, cli_data):
#         """
#         Add metadata on a specific cli
#         :param cli_name: the name of the cli
#         :param cli_data: a dictionary following the format:
#                     {
#                       type: < type >
#                       xml: < xml >

#                     }
#         The data is passed in a s a dictionary in the case the more metadata
#         is added to eh cli description
#         """
#         self.data[DockerImage.cli_dict][cli_name] = cli_data

#     @staticmethod
#     def getHashKey(imgName):
#         """
#         Generates a hash key (on the docker image name) used by the DockerImage
#          object to provide a means to uniquely find the image metadata
#          in the girder-mongo database. This prevents user defined image name
#          from causing issues with pymongo.Note this key is not the same as the
#          docker image id that the docker engine generates
#         :imgName: The name of the docker image

#         :returns: The hashkey as a string
#         """
#         imageKey = hashlib.sha256(imgName.encode()).hexdigest()
#         return imageKey

#     def getCLIKeys(self):
#         return list(self.data[DockerImage.cli_dict].keys())

#     def getRawData(self):
#         return self.data
