# -*- coding: utf-8 -*-

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

from girder.models.setting import Setting
from girder.utility import setting_utilities
from girder.settings import SettingDefault


# Constants representing the setting keys for this plugin
class PluginSettings(object):
    SLICER_CLI_WEB_DEFAULT_TASK_FOLDER = 'slicer_cli_web.task_folder'

    @staticmethod
    def get_default_folder():
        return Setting().get(PluginSettings.SLICER_CLI_WEB_DEFAULT_TASK_FOLDER)


@setting_utilities.validator({
    PluginSettings.SLICER_CLI_WEB_DEFAULT_TASK_FOLDER
})
def validateFolder(doc):
    # TODO
    doc['value'] = str(doc['value']).strip()


# Defaults

# Defaults that have fixed values can just be added to the system defaults
# dictionary.
SettingDefault.defaults.update({
    PluginSettings.SLICER_CLI_WEB_DEFAULT_TASK_FOLDER: None
})
