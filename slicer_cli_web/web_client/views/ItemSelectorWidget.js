import $ from 'jquery';
import _ from 'underscore';

import { getCurrentUser } from '@girder/core/auth';
import BrowserWidget from '@girder/core/views/widgets/BrowserWidget';
import FileModel from '@girder/core/models/FileModel';
import ItemModel from '@girder/core/models/ItemModel';
import { restRequest } from '@girder/core/rest';

const ItemSelectorWidget = BrowserWidget.extend({
    initialize(settings) {
        if (!this.model) {
            this.model = new ItemModel();
        }
        const t = this.model.get('type');
        settings.showItems = true;
        settings.submitText = 'Confirm';
        settings.validate = (model) => this._validateModel(model);
        settings.root = settings.rootPath || getCurrentUser();
        if (settings.root === false) {
            settings.root = null;
        }

        switch (t) {
            case 'directory':
                settings.titleText = 'Select a directory';
                break;
            case 'file':
                settings.titleText = 'Select a file';
                settings.selectItem = true;
                settings.showPreview = false;
                break;
            case 'image':
                settings.titleText = 'Select an image';
                settings.selectItem = true;
                settings.showPreview = false;
                break;
            case 'item':
                settings.titleText = 'Select an item';
                settings.selectItem = true;
                settings.showPreview = false;
                break;
            case 'new-file':
                settings.titleText = 'Select a directory';
                settings.input = {
                    label: 'Item name',
                    validate: (val) => {
                        if (val && val.trim()) {
                            return $.Deferred().resolve().promise();
                        }
                        return $.Deferred().reject('Specify an item name').promise();
                    }
                };
                settings.showPreview = false;
                break;
        }
        settings.titleText += ` for "${this.model.get('title')}"`;

        this.on('g:saved', (model, fileName) => this._saveModel(model, fileName));
        return BrowserWidget.prototype.initialize.apply(this, arguments);
    },

    render() {
        BrowserWidget.prototype.render.apply(this, arguments);
        const t = this.model.get('type');
        if (['file', 'image', 'item'].includes(t)) {
            this.$('.modal-footer').hide();
        }
        return this;
    },

    /**
     * Get the currently displayed path in the hierarchy view.
     */
    _path() {
        let path = this._hierarchyView.breadcrumbs.map((d) => d.get('name'));

        if (this.model.get('type') === 'directory') {
            path = _.initial(path);
        }
        return path;
    },

    _validateModel(model) {
        const t = this.model.get('type');
        let error;

        switch (t) {
            case 'directory':
            case 'new-file':
                if (!model || model.get('_modelType') !== 'folder') {
                    error = 'Select a directory.';
                }
                break;
            case 'file':
                if (!model) {
                    error = 'Select a file.';
                } else {
                    const result = $.Deferred();
                    restRequest({url: `/item/${model.id}/files`, data: {limit: 1}}).done((resp) => {
                        if (!resp.length) {
                            result.reject('Please select a item with at least one file.');
                        }
                        result.resolve(null);
                    }).fail(() => {
                        result.reject('There was an error listing files for the selected item.');
                    });
                    return result.promise();
                }
                break;
            case 'image':
                if (!model) {
                    error = 'Select an image.';
                } else if (!model.get('largeImage')) {
                    error = 'Please select a "large_image" item.';
                }
                break;
            case 'item':
                if (!model) {
                    error = 'Select an item.';
                }
                break;
        }
        if (error) {
            return $.Deferred().reject(error).promise();
        }
        return $.Deferred().resolve().promise();
    },

    _saveModel(model, fileName) {
        const t = this.model.get('type');

        switch (t) {
            case 'directory':
                this.model.set({
                    path: this._path(),
                    value: model
                });
                break;
            case 'file':
                restRequest({url: `/item/${model.id}/files`, data: {limit: 1}}).done((resp) => {
                    if (!resp.length) {
                        return;
                    }
                    const file = new FileModel({_id: resp[0]._id});
                    file.once('g:fetched', () => {
                        this.model.set({
                            path: this._path(),
                            value: file
                        });
                    }).fetch();
                });
                break;
            case 'image': {
                const image = model.get('largeImage');
                // Prefer the large_image fileId
                const file = new FileModel({ _id: image.fileId || image.originalId });
                file.once('g:fetched', () => {
                    this.model.set({
                        path: this._path(),
                        value: file
                    });
                }).fetch();
                break;
            }
            case 'item':
                this.model.set({
                    path: this._path(),
                    value: model
                });
                break;
            case 'new-file':
                this.model.set({
                    path: this._path(),
                    parent: model,
                    value: new ItemModel({
                        name: fileName,
                        folderId: model.id
                    })
                });
                break;
        }
    },

    _selectItem: function (item) {
        BrowserWidget.prototype._selectItem.apply(this, arguments);
        if (this.selectItem) {
            this.$('.g-submit-button').click();
        }
    }
});

export default ItemSelectorWidget;
