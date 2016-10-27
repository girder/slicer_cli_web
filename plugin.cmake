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

add_python_test(import PLUGIN slicer_cli_web)

add_python_test(docker PLUGIN slicer_cli_web)

# front-end tests
add_web_client_test(
    slicer_cli_web_schema "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/plugin_tests/client/parser.js"
    ENABLEDPLUGINS "slicer_cli_web")

add_web_client_test(
    slicer_cli_web_widget "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/plugin_tests/client/widget.js"
    ENABLEDPLUGINS "slicer_cli_web")

add_eslint_test(
  js_static_analysis_slicer_cli_web "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/web_client"
  ESLINT_CONFIG_FILE "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/.eslintrc"
  ESLINT_IGNORE_FILE "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/.eslintignore"
)

add_eslint_test(
  js_static_analysis_slicer_cli_web_tests "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/plugin_tests/client"
  ESLINT_CONFIG_FILE "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/plugin_tests/client/.eslintrc"
  ESLINT_IGNORE_FILE "${PROJECT_SOURCE_DIR}/plugins/slicer_cli_web/.eslintignore"
)

add_puglint_test(
  slicer_cli_web
  "${CMAKE_CURRENT_LIST_DIR}/web_client/templates"
)
