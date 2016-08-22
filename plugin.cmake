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

# style tests
add_python_style_test(
  python_static_analysis_slicer_cli_web_plugins
  "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/server"
)

add_python_style_test(
  python_static_analysis_slicer_cli_web_tests
  "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/plugin_tests")


# API tests
add_python_test(example PLUGIN slicer_cli_web)

add_python_test(docker PLUGIN slicer_cli_web)


