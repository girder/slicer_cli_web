import $ from 'jquery';
import _ from 'underscore';

import { getCurrentUser } from '@girder/core/auth';
import BrowserWidget from '@girder/core/views/widgets/BrowserWidget';
import FileModel from '@girder/core/models/FileModel';
import ItemModel from '@girder/core/models/ItemModel';
import FolderModel from '@girder/core/models/FolderModel';
import UserModel from '@girder/core/models/FolderModel';
import CollectionModel from '@girder/core/models/CollectionModel';
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
        if (settings.root === false || settings.defaultSelectedResource) {
            settings.root = null;
        }

        settings.paginated = true;

        /**
         * I need to type this out
         * If we have 'value' we need to look for an itemId or a folderID, if we have a folderID we should have a defaultResource we can point to
         * 
         * If we don't have 'value' we need to look for an itemID to get the eventual folderId used for
         */

        if (this.model.get('value')){       
            this.getRoot(this.model.get('value'), settings);
        } 
            return this.completeInitialization(settings);

    },

    getRoot(resource, settings) {

        const modelTypes = {
            item: ItemModel,
            folder: FolderModel,
            collection: CollectionModel,
            user: UserModel
        };
        let modelType = 'folder'; // folder type by default, other types if necessary
        let modelId = null;
        // If it is an item it will have a folderId associated with it as a parent item
        if (resource.get('itemId')) {
            modelId = resource.get('itemId');
            modelType = 'item';
        } else if (resource.get('folderId')) {
            modelId = resource.get('folderId');
        } else if (resource.get('parentCollection')) {
            // Case for providing a folder as the defaultSelectedResource but want the user to select an item
            // folder parent is either 'user' | 'folder' | 'collection', most likely folder though
            modelType = resource.get('parentCollection');
            modelId = resource.get('parentId');
        }
        // We need to fetch the itemID to get the model stuff
        if (modelType === 'item') {
            const itemModel = new modelTypes[modelType]();
            itemModel.set({
                _id: modelId
            }).on('g:fetched', function () {
                settings.defaultSelectedResource = itemModel;
                settings.highlightItem = true;
                settings.selectItem = true;
                this.getRoot(itemModel, settings)
            }, this).on('g:error', function () {
                settings.root = null;
                this.completeInitialization(settings)
            }, this).fetch();
        }
        else if (modelTypes[modelType] && modelId) {
            const parentModel = new modelTypes[modelType]();
            parentModel.set({
                _id: modelId
            }).on('g:fetched', function () {
                settings.root = parentModel;
                settings.rootSelectorSettings.selectByResource = parentModel;
                this.completeInitialization(settings);
                this.render();
                if (this.model.get('type') === 'multi') {
                    this.processRegularExpression();
                }
            }, this).on('g:error', function () {
                settings.root = null;
                this.completeInitialization(settings)
                this.render();
            }, this).fetch();
        }
    },

    completeInitialization(settings){

        const t = this.model.get('type');
        switch (t) {
            case 'directory':
                settings.titleText = 'Select a directory';
                break;
            case 'file':
                settings.titleText = 'Select a file';
                settings.selectItem = true;
                settings.highlightItem = true;
                settings.showPreview = false;
                break;
            case 'image':
                settings.titleText = 'Select an image';
                settings.selectItem = true;
                settings.highlightItem = true;
                settings.showPreview = false;
                break;
            case 'item':
                settings.titleText = 'Select an item';
                settings.selectItem = true;
                settings.highlightItem = true;
                settings.showPreview = false;
                break;
            case 'multi':
                settings.titleText = 'Select files';
                settings.selectItem = false;
                settings.input = {
                    label: 'Item Filter (Regular Expression)',
                    validate: (val) => {
                        try {
                            const regExp = RegExp(val);
                            if (regExp) {
                                return $.Deferred().resolve().promise();
                            }
                        } catch (exception) {
                            return $.Deferred().reject('Specify a valid Regular Expression').promise();
                        }
                    }
                };
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

       return  BrowserWidget.prototype.initialize.apply(this, arguments);
    },

    render() {
        BrowserWidget.prototype.render.apply(this, arguments);

        const t = this.model.get('type');
        if (['file', 'image', 'item'].includes(t)) {
            this.$('.modal-footer').hide();
        }
        if (t === 'multi') {
            this.$('#g-input-element').attr('placeholder', '(all)');
            this.$('.g-item-list-entry').addClass('g-selected');

            this.$('#g-input-element').on('input', () => this.processRegularExpression());
                if (this.model.get('value') && this.model.get('value').get('name')){
                    this.$('#g-input-element').val(this.model.get('value').get('name'));
                }    
                this.processRegularExpression();
        }
        return this;
    },

    /**
     * While type is multi this will check the input element for a regular expression.
     * Will apply highlighting to existing items if a valid expression
     * If not valid it will provide feedback to the user that it is invalid
     */
    processRegularExpression() {
        const reg = this.$('#g-input-element').val();
        this.$('.g-item-list-entry').removeClass('g-selected');
        try {
            const regEx = new RegExp(reg, 'g');
            this.$('.g-validation-failed-message').addClass('hidden');
            this.$('.g-input-element.form-group').removeClass('has-error');

            this.$('.g-item-list-link').each((index, item) => {
                if (this.$(item)) {
                    // Cloning to remove the Thumbnail counter text
                    const text = this.$(item).clone()
                        .children()
                        .remove()
                        .end()
                        .text();
                    if (text.match(regEx) || reg === '') {
                        this.$(item).parent().addClass('g-selected');
                    }
                }
            });
        } catch (exception) {
            if (exception instanceof SyntaxError) {
                this.$('.g-validation-failed-message').text('Specify a valid Regular Expression');
                this.$('.g-validation-failed-message').removeClass('hidden');
                this.$('.g-input-element.form-group').addClass('has-error');
            }
        }
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
    /**
     * Checks when the model changes and binds to the changed of itemListView to select items in multi mode
     */
    _selectModel() {
        BrowserWidget.prototype._selectModel.apply(this, arguments);
        if (this.model.get('type') === 'multi' && this._hierarchyView && this._hierarchyView.itemListView) {
            this._hierarchyView.itemListView.once('g:changed', (evt) => {
                this.processRegularExpression();
            });
        }
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
            case 'multi':
                if (fileName.trim() === '') {
                    fileName = '.*';
                }
                this.model.set({
                    path: this._path(),
                    parent: model,
                    folderName: model.name(),
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
