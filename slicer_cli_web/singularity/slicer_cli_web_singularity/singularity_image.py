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

import json

from girder.constants import AccessType
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item

from .commands import SingularityCommands, run_command
from slicer_cli_web.models.parser import parse_json_desc, parse_xml_desc, parse_yaml_desc
from slicer_cli_web.models.docker_image import CLIItem


def sanitize_and_return_json(res: str):
    '''
    This function tries to parse the given str as json in couple different ways. If the output is still not json or a python dictionary, it raises an error.
    '''
    try:
        res = json.loads(res)
        # This is the form in which we get data back if we use the --json label in
        # singularity inspect
        return res['data']['attributes']['labels']
    except json.decoder.JSONDecodeError as e:
        # If the json label was excluded, we can still parse the labels manually
        # and create a dictionary
        labels = [line for line in res.split('\n')]
        res_dict = {}
        for label in labels:
            key, value = label.split(': ')
            res_dict[key] = value
        return res_dict
    except Exception as e:
        raise Exception(f'Error occured when parsing labels as json {e}')


def _split(name):
    """
    :param name: image name
    :type name: string
    """
    if ':' in name:
        return name.split(':')
    return name.split('@')


class SingularityImage:
    '''
    This class is used to produce the Singularity equivalent of the Docker Image object as part of the Python SDK. This helps us to
    reuse all the functions where Docker is not not directly involved rather the snapshort of the Docker Image object should suffice to perform the necessaray operations
    '''

    def __init__(self, local_sif_file: str):
        self.id = None
        self.labels = None
        self.short_id = None
        self.tags = None
        self._set_all_fields(local_sif_file)

    def _set_all_fields(self, local_sif_file: str):
        inspect_labels_cmd = SingularityCommands.singularity_inspect(local_sif_file)
        try:
            res = run_command(inspect_labels_cmd)
            # Convert the string labels into json format and only get the labels part from the code
            res = sanitize_and_return_json(res)
            self.id = res.get('id', '')
            self.labels = res
            self.tags = res.get('tags', '')
            self.short_id = res.get('short_id', '')
        except Exception as e:
            raise Exception(f"Failed to add metadata from Singularity Image \n {e} \n")

    # A get method to retrieve any label necessary or None, in order to avoid
    # errors in certain portions of the code and better emulate Docker Image
    # Object behavior
    def get(self, label: str):
        return self.labels.get(label, None)


class SingularityImageItem:
    def __init__(self, imageFolder, tagFolder, user):
        self.image = imageFolder['name']
        self.tag = tagFolder['name']
        self.name = '%s:%s' % (self.image, self.tag)
        self.imageFolder = imageFolder
        self.tagFolder = tagFolder
        self._id = self.tagFolder['_id']
        self.user = user
        self.name = '%s:%s' % (self.image, self.tag)
        self.digest = tagFolder['meta'].get('digest', self.name)

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
        return SingularityImageItem(imageFolder, tagFolder, user)

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
                images.append(SingularityImageItem(imageFolder, tagFolder, user))
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

            if folderModel.hasAccess(imageFolder, user, AccessType.WRITE) and \
               folderModel.countFolders(imageFolder) == 0:
                # clean also empty image folders
                folderModel.remove(imageFolder)

        return removed

    @staticmethod
    def _create(name, singularity_image_object, user, baseFolder):
        folderModel = Folder()
        fileModel = File()

        imageName, tagName = _split(name)

        image = folderModel.createFolder(baseFolder, imageName,
                                         'Slicer CLI generated docker image folder',
                                         creator=user, reuseExisting=True)
        folderModel.setMetadata(image, dict(slicerCLIType='image'))

        fileModel.createLinkFile('Docker Hub', image, 'folder',
                                 'https://hub.docker.com/r/%s' % imageName,
                                 user, reuseExisting=True)

        tag = folderModel.createFolder(image, tagName,
                                       'Slicer CLI generated docker image tag folder',
                                       creator=user, reuseExisting=True)

        # add docker image labels as meta data
        labels = {} if not singularity_image_object.labels else singularity_image_object.labels.copy()
        if 'description' in labels:
            tag['description'] = labels['description']
            del labels['description']
        labels = {k.replace('.', '_'): v for k, v in labels.items()}
        labels['digest'] = singularity_image_object.get('digest')
        folderModel.setMetadata(tag, labels)

        folderModel.setMetadata(tag, dict(slicerCLIType='tag'))

        return SingularityImageItem(image, tag, user)

    @staticmethod
    def _syncItems(image, cli_dict, user):
        folderModel = Folder()
        itemModel = Item()

        children = folderModel.childItems(image.tagFolder, filters={'meta.slicerCLIType': 'task'})
        existingItems = {item['name']: item for item in children}

        for cli, desc in cli_dict.items():
            item = itemModel.createItem(cli, user, image.tagFolder,
                                        'Slicer CLI generated CLI command item',
                                        reuseExisting=True)
            meta_data = dict(slicerCLIType='task', type=desc.get('type', 'Unknown'))

            # copy some things from the image to be independent
            meta_data['image'] = image.name
            meta_data['digest'] = image.digest if image.name != image.digest else None
            if desc.get('docker-params'):
                meta_data['docker-params'] = desc['docker-params']

            desc_type = desc.get('desc-type', 'xml')

            if desc_type == 'xml':
                meta_data.update(parse_xml_desc(item, desc, user))
            elif desc_type == 'yaml':
                meta_data.update(parse_yaml_desc(item, desc, user))
            elif desc_type == 'json':
                meta_data.update(parse_json_desc(item, desc, user))

            itemModel.setMetadata(item, meta_data)

            if cli in existingItems:
                del existingItems[cli]

        # delete superfluous items
        for item in existingItems.values():
            itemModel.remove(item)

    @staticmethod
    def saveImage(name, cli_dict, singularity_image_object, user, baseFolder):
        """
        :param baseFolder
        :type Folder
        """
        image = SingularityImageItem._create(name, singularity_image_object, user, baseFolder)
        SingularityImageItem._syncItems(image, cli_dict, user)

        return image

    @staticmethod
    def prepare():
        Item().ensureIndex(['meta.slicerCLIType', {'sparse': True}])
