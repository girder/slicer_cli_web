/**
 * Copyright 2015 Kitware Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
module.exports = function (grunt) {
    grunt.config.merge({
        slicer: {
            root: '<%= pluginDir %>/slicer_cli_web',
            extjs: '<%= slicer.root %>/web_client/js/ext',
            extcss: '<%= slicer.root %>/web_client/stylesheets/ext',
            extextra: '<%= slicer.root %>/web_client/extra',
            npm: '<%= slicer.root %>/node_modules',
            external: '<%= slicer.root %>/web_main',
            static: '<%= staticDir %>/built/plugins/slicer_cli_web'
        },
        uglify: {
            'slicer-main': {
                files: [
                    {
                        src: [
                            '<%= slicer.external %>/main.js'
                        ],
                        dest: '<%= slicer.static %>/slicer.main.min.js'
                    }
                ]
            }
        },
        jade: {
            'plugin-slicer_cli_web': {
                options: {
                    namespace: 'slicer.templates'
                }
            }
        },
        copy: {
            'bootstrap-slider': {
                files: [{
                    '<%= slicer.extjs %>/bootstrap-slider.js': '<%= slicer.npm %>/bootstrap-slider/dist/bootstrap-slider.js',
                    '<%= slicer.extcss %>/bootstrap-slider.css': '<%= slicer.npm %>/bootstrap-slider/dist/css/bootstrap-slider.css'
                }]
            },
            'bootstrap-colorpicker': {
                files: [{
                    '<%= slicer.extjs %>/bootstrap-colorpicker.js': '<%= slicer.npm %>/bootstrap-colorpicker/dist/js/bootstrap-colorpicker.js',
                    '<%= slicer.extcss %>/bootstrap-colorpicker.css': '<%= slicer.npm %>/bootstrap-colorpicker/dist/css/bootstrap-colorpicker.css'
                }, {
                    expand: true,
                    cwd: '<%= slicer.npm %>/bootstrap-colorpicker/dist/img',
                    src: ['bootstrap-colorpicker/*.png'],
                    dest: '<%= slicer.extextra %>'
                }]
            },
            tinycolor:  {
                files: [{
                    '<%= slicer.extjs %>/tinycolor.js': '<%= slicer.npm %>/tinycolor2/tinycolor.js'
                }]
            }
        },
        stylus: {
            'plugin-slicer_cli_web': {
                options: {
                    'include css': true
                }
            }
        },
        init: {
            'copy:bootstrap-slider': {
                dependencies: [
                    'shell:plugin-slicer_cli_web'
                ]
            },
            'copy:bootstrap-colorpicker': {
                dependencies: [
                    'shell:plugin-slicer_cli_web'
                ]
            },
            'copy:tinycolor': {
                dependencies: [
                    'shell:plugin-slicer_cli_web'
                ]
            }
        },
        default: {
            'uglify:slicer-main': {}
        },
        watch: {
            'plugin-slicer-uglify-main': {
                files: ['<%= slicer.external %>/**/*.js'],
                tasks: ['uglify:slicer-main']
            }
        }
    });
};
