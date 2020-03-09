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
        $('<button class="g-upload-slicer-cli-task-button btn btn-sm btn-default" title="Upload CLI Slicer Task"><i class="icon-upload"></i></button>')
            .insertAfter(button)
            .on('click', () => {
                new UploadImageDialog({
                    model: this.model,
                    parentView: this,
                    el: $('#g-dialog-container')
                }).render();
            });
    };

    if (getCurrentUser() && getCurrentUser().get('admin')) {
        if (this.parentModel.get('_modelType') === 'folder') {
            ConfigView.getSettings().then((settings) => {
                if (settings.task_folder === this.parentModel.id) {
                    injectUploadImageButton();
                }
                return null;
            });
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
