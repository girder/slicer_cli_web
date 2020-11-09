import $ from 'jquery';
import View from '@girder/core/views/View';

import BrowserWidget from '@girder/core/views/widgets/BrowserWidget';
import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';
import { showJobSuccessAlert } from './utils';

/**
 * Show the default quota settings for users and collections.
 */
const ConfigView = View.extend({
    events: {
        'submit #g-slicer-cli-web-form'(event) {
            event.preventDefault();
            this.$('#g-slicer-cli-web-error-message').empty();
            this._saveSettings([{
                key: 'slicer_cli_web.task_folder',
                value: this.$('#g-slicer-cli-web-upload-folder').val()
            }]);
        },
        'submit #g-slicer-cli-web-upload-form'(event) {
            event.preventDefault();
            this.$('#g-slicer-cli-web-error-upload-message').empty();
            this._uploadImage(
                $('#g-slicer-cli-web-image').val(),
                $('#g-slicer-cli-web-folder').val());
        },
        'click .g-open-browser': '_openBrowser',
        'click .g-open-local-browser': '_openLocalBrowser'
    },

    initialize() {
        this._browserWidgetView = new BrowserWidget({
            parentView: this,
            titleText: 'Task Upload Folder',
            helpText: 'Browse to a location to select it as the upload folder.',
            submitText: 'Select Folder',
            validate(model) {
                const isValid = $.Deferred();
                if (!model) {
                    isValid.reject('Please select a valid root.');
                } if (model.get('_modelType') !== 'folder') {
                    isValid.reject('Please select a folder.');
                } else {
                    isValid.resolve();
                }
                return isValid.promise();
            },
            rootSelectorSettings: {
                pageLimit: 1000
            }
        });
        this.listenTo(this._browserWidgetView, 'g:saved', (val) => {
            if (!this._localOnly) {
                this.$('#g-slicer-cli-web-upload-folder').val(val.id);
            }
            this.$('#g-slicer-cli-web-folder').val(val.id);
        });

        ConfigView.getSettings().then((settings) => {
            this.settings = settings;
            this.render();
            return null;
        });
    },

    render() {
        this.$el.html(ConfigViewTemplate({
            settings: this.settings
        }));
        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Slicer CLI Web',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _uploadImage(imagename, folderid) {
        /* Now submit */
        const name = imagename.split(',').map((d) => d.trim()).filter((d) => d.length > 0);
        return restRequest({
            method: 'PUT',
            url: 'slicer_cli_web/docker_image',
            data: {
                name: JSON.stringify(name),
                folder: folderid
            },
            error: null
        }).done((job) => {
            showJobSuccessAlert(job);
        }).fail((resp) => {
            this.$('#g-slicer-cli-web-error-upload-message').text(
                resp.responseJSON.message
            );
        });
    },

    _openBrowser() {
        this._localOnly = false;
        this._browserWidgetView.setElement($('#g-dialog-container')).render();
    },
    _openLocalBrowser() {
        this._localOnly = true;
        this._browserWidgetView.setElement($('#g-dialog-container')).render();
    },

    _saveSettings(settings) {
        /* Now save the settings */
        return restRequest({
            method: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            ConfigView.clearSettingsCache();
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-slicer-cli-web-error-message').text(
                resp.responseJSON.message
            );
        });
    }
}, {
    clearSettingsCache() {
        delete ConfigView.settings;
    },
    getSettings() {
        if (ConfigView.settings) {
            return ConfigView.settings;
        }
        ConfigView.settings = restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify(['slicer_cli_web.task_folder'])
            }
        }).then((resp) => {
            const settings = {
                task_folder: resp['slicer_cli_web.task_folder']
            };

            return settings;
        });
        return ConfigView.settings;
    }
});

export default ConfigView;
