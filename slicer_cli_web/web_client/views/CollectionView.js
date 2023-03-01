import $ from 'jquery';
import { wrap } from '@girder/core/utilities/PluginUtils';
import { restRequest } from '@girder/core/rest';
import View from '@girder/core/views/View';
import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import { getCurrentUser } from '@girder/core/auth';

import UploadImageDialogTemplate from '../templates/uploadImageDialog.pug';
import { showJobSuccessAlert } from './utils';
import ConfigView from './ConfigView';
import '@girder/core/utilities/jquery/girderModal';

wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    const injectUploadImageButton = () => {
        const button = this.$('.g-upload-here-button');
        if (button.length === 0) {
            return;
        }
        $('<button class="g-upload-slicer-cli-task-button btn btn-sm btn-default" title="Upload CLI Slicer Task" style="height: calc(1.5em + 10px);line-height: 0.75em"><i class="icon-upload"></i><div style="font-size: 0.75em;">CLI</div></button>')
            .insertAfter(button)
            .on('click', () => {
                new UploadImageDialog({
                    model: this.model,
                    parentView: this,
                    el: $('#g-dialog-container')
                }).render();
            });
    };

    const injectReloadImageButton = (imageName, folderId) => {
        const button = this.$('.g-upload-here-button');
        if (button.length === 0) {
            return;
        }
        $('<button class="g-repull-slicer-cli-task-button btn btn-sm btn-default">Pull Latest</button>').attr('title', 'Pull latest and reload ' + imageName)
            .insertAfter(button)
            .on('click', () => restRequest({
                method: 'PUT',
                url: 'slicer_cli_web/docker_image',
                data: {
                    name: JSON.stringify(imageName),
                    folder: folderId,
                    pull: 'true'
                },
                error: null
            }).done((job) => {
                showJobSuccessAlert(job);
            }));
        $('<button class="g-reload-slicer-cli-task-button btn btn-sm btn-default">Reload CLI Image</button>').attr('title', 'Reload ' + imageName)
            .insertAfter(button)
            .on('click', () => restRequest({
                method: 'PUT',
                url: 'slicer_cli_web/docker_image',
                data: {
                    name: JSON.stringify(imageName),
                    folder: folderId
                },
                error: null
            }).done((job) => {
                showJobSuccessAlert(job);
            }));
    };

    if (getCurrentUser() && getCurrentUser().get('admin')) {
        if (this.parentModel.get('_modelType') === 'folder') {
            ConfigView.getSettings().then((settings) => {
                if (settings.task_folder === this.parentModel.id) {
                    injectUploadImageButton();
                }
                return null;
            });
            try {
                if (this.parentModel.get('meta').slicerCLIType === 'tag' && this.parentView.hierarchyWidget.breadcrumbs[this.parentView.hierarchyWidget.breadcrumbs.length - 2].get('meta').slicerCLIType === 'image') {
                    let imageAndTag = this.parentView.hierarchyWidget.breadcrumbs[this.parentView.hierarchyWidget.breadcrumbs.length - 2].get('name') + ':' + this.parentModel.get('name');
                    let folderId = this.parentView.hierarchyWidget.breadcrumbs[this.parentView.hierarchyWidget.breadcrumbs.length - 3].id;
                    injectReloadImageButton(imageAndTag, folderId);
                }
            } catch (err) {}
        }
    }
});

const UploadImageDialog = View.extend({
    events: {
        'submit #g-slicer-cli-web-upload-form'(e) {
            e.preventDefault();
            this.$('#g-slicer-cli-web-error-upload-message').empty();
            this._uploadImage(new FormData(e.currentTarget));
        }
    },
    render() {
        this.$el.html(UploadImageDialogTemplate());
        this.$el.girderModal(this);
        return this;
    },

    _uploadImage(data) {
        /* Now submit */
        const name = data.get('name').split(',').map((d) => d.trim()).filter((d) => d.length > 0);
        return restRequest({
            method: 'PUT',
            url: 'slicer_cli_web/docker_image',
            data: {
                name: JSON.stringify(name)
            },
            error: null
        }).done((job) => {
            this.$el.girderModal('close');
            showJobSuccessAlert(job);
        }).fail((resp) => {
            this.$('#g-slicer-cli-web-error-upload-message').text(
                resp.responseJSON.message
            );
        });
    }
});
