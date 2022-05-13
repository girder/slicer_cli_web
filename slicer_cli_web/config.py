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

from girder.api.rest import getCurrentUser
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.settings import SettingDefault
from girder.utility import setting_utilities


# Constants representing the setting keys for this plugin
class PluginSettings:
    SLICER_CLI_WEB_TASK_FOLDER = 'slicer_cli_web.task_folder'

    @staticmethod
    def has_task_folder():
        return Setting().get(PluginSettings.SLICER_CLI_WEB_TASK_FOLDER) is not None

    @staticmethod
    def get_task_folder():
        folder = Setting().get(PluginSettings.SLICER_CLI_WEB_TASK_FOLDER)
        if not folder:
            return None
        return Folder().load(folder, level=AccessType.READ, user=getCurrentUser())


@setting_utilities.validator({
    PluginSettings.SLICER_CLI_WEB_TASK_FOLDER
})
def validateFolder(doc):
    if not doc['value']:
        return
    # We should only be able to change settings with admin privilege, so we
    # don't need to check folder access here.
    folder = Folder().load(doc['value'], force=True)
    if not folder:
        raise ValidationException('invalid folder selected')


# Defaults

# Defaults that have fixed values can just be added to the system defaults
# dictionary.
SettingDefault.defaults.update({
    PluginSettings.SLICER_CLI_WEB_TASK_FOLDER: None
})
