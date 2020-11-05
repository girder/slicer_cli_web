import $ from 'jquery';
import _ from 'underscore';
import moment from 'moment';

import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { getCurrentUser } from '@girder/core/auth';
import FolderCollection from '@girder/core/collections/FolderCollection';
import ItemModel from '@girder/core/models/ItemModel';
import FileModel from '@girder/core/models/FileModel';
import FolderModel from '@girder/core/models/FolderModel';
import { restRequest } from '@girder/core/rest';

import ItemSelectorWidget from './ItemSelectorWidget';

import booleanWidget from '../templates/booleanWidget.pug';
import colorWidget from '../templates/colorWidget.pug';
import enumerationWidget from '../templates/enumerationWidget.pug';
import fileWidget from '../templates/fileWidget.pug';
import rangeWidget from '../templates/rangeWidget.pug';
import regionWidget from '../templates/regionWidget.pug';
import widget from '../templates/widget.pug';

import '../stylesheets/controlWidget.styl';
import 'bootstrap-colorpicker/dist/js/bootstrap-colorpicker';
import 'bootstrap-colorpicker/dist/css/bootstrap-colorpicker.css';
import 'bootstrap-slider/dist/bootstrap-slider';
import 'bootstrap-slider/dist/css/bootstrap-slider.css';

const ControlWidget = View.extend({
    events: {
        'change input,select': '_input',
        changeColor: '_input',
        'click .s-select-file-button': '_selectFile',
        'click .s-select-region-button': '_selectRegion'
    },

    initialize(settings) {
        this._disableRegionSelect = settings.disableRegionSelect === true;
        this._rootPath = settings.rootPath;
        this.listenTo(this.model, 'change', this.change);
        this.listenTo(this.model, 'destroy', this.remove);
        this.listenTo(this.model, 'invalid', this.invalid);
        this.listenTo(events, 's:widgetSet:' + this.model.id, (value) => {
            this.model.set('value', value);
        });

        this._initModel(settings);
    },

    _initModel(settings) {
        const prefix = settings.setDefaultOutput;
        const model = this.model;
        const type = model.get('type');
        const channel = model.get('channel');
        const required = model.get('required');
        if (channel === 'input') {
            if (model.get('defaultNameMatch') || model.get('defaultPathMatch')) {
                this._getDefaultInputResource(model).then((resource) => {
                    if (!resource) {
                        return null;
                    }
                    this.model.set({
                        value: resource
                    });
                    return null;
                });
            }
        }
        if (!prefix || !required || channel !== 'output' || !['new-file', 'file', 'item', 'directory'].includes(type)) {
            return;
        }
        this._getDefaultOutputFolder().then((folder) => {
            if (!folder) {
                return null;
            }
            const extension = (model.get('extensions') || '').split('|')[0];
            const modelName = model.get('id') === 'returnparameterfile' ? '' : `-${model.get('title')}`;
            const reference = this._findReference();
            if (reference) {
                this.listenTo(reference, 'change', () => {
                    const value = reference.get('value');
                    if (value && value.get('name')) {
                        let refName = value.get('name');
                        if (refName.includes('.')) {
                            refName = refName.slice(0, refName.lastIndexOf('.'));
                        }
                        const name = `${refName}-${prefix}${modelName}-${moment().local().format()}${extension}`;
                        this._setValue(folder, name);
                    }
                });
            } else {
                const name = `${prefix}${modelName}-${moment().local().format()}${extension}`;
                this._setValue(folder, name);
            }
            return null;
        });
    },

    _setValue(folder, name) {
        this.model.set({
            path: [folder.get('name'), name],
            parent: folder,
            value: new ItemModel({
                name,
                folderId: folder.id
            })
        });
    },

    _findReference() {
        const ref = this.model.get('reference');
        if (!ref) {
            return null;
        }
        // ref is an id of another model
        return this.model.collection.find((d) => d.get('id') === ref);
    },

    render(_, options) {
        this.$('.form-group').removeClass('has-error');
        this.model.isValid();
        if (options && options.norender) {
            return this;
        }
        const params = Object.assign({
            disableRegionSelect: this._disableRegionSelect
        }, this.model.toJSON());
        this.$el.html(this.template()(params));
        this.$('.s-control-item[data-type="range"] input').slider();
        this.$('.s-control-item[data-type="color"] .input-group').colorpicker({});
        this.$('[data-toggle="tooltip"]').tooltip({container: 'body'});
        return this;
    },

    change() {
        events.trigger(`s:widgetChanged:${this.model.get('type')}`, this.model);
        events.trigger('s:widgetChanged', this.model);
        this.render.apply(this, arguments);
    },

    remove() {
        events.trigger(`s:widgetRemoved:${this.model.get('type')}`, this.model);
        events.trigger('s:widgetRemoved', this.model);
        this.$('.s-control-item[data-type="color"] .input-group').colorpicker('destroy');
        this.$('.s-control-item[data-type="range"] input').slider('destroy');
        this.$el.empty();
    },

    /**
     * Set classes on the input element to indicate to the user that the current value
     * is invalid.  This is automatically triggered by the model's "invalid" event.
     */
    invalid() {
        events.trigger(`s:widgetInvalid:${this.model.get('type')}`, this.model);
        events.trigger('s:widgetInvalid', this.model);
        this.$('.form-group').addClass('has-error');
    },

    /**
     * Type definitions mapping used internally.  Each widget type
     * specifies it's pug template and possibly more customizations
     * as needed.
     */
    _typedef: {
        range: {
            template: rangeWidget
        },
        color: {
            template: colorWidget
        },
        string: {
            template: widget
        },
        number: {
            template: widget
        },
        integer: {
            template: widget
        },
        boolean: {
            template: booleanWidget
        },
        'string-vector': {
            template: widget
        },
        'number-vector': {
            template: widget
        },
        'string-enumeration': {
            template: enumerationWidget
        },
        'number-enumeration': {
            template: enumerationWidget
        },
        file: {
            template: fileWidget
        },
        item: {
            template: fileWidget
        },
        image: {
            template: fileWidget
        },
        directory: {
            template: fileWidget
        },
        'new-file': {
            template: fileWidget
        },
        region: {
            template: regionWidget
        }
    },

    /**
     * Get the appropriate template for the model type.
     */
    template() {
        const type = this.model.get('type');
        let def = this._typedef[type];

        if (def === undefined) {
            console.warn('Invalid widget type "' + type + '"'); // eslint-disable-line no-console
            def = {};
        }
        return def.template || _.template('');
    },

    /**
     * Get the current value from an input (or select) element.
     */
    _input(evt) {
        const $el = $(evt.target);
        let val = $el.val();

        if ($el.attr('type') === 'checkbox') {
            val = $el.get(0).checked;
        }

        // we don't want to rerender, because this event is generated by the input element
        this.model.set('value', val, {norender: true});
    },

    /**
     * Get the value from a file selection modal and set the text in the widget's
     * input element.
     */
    _selectFile() {
        const modal = new ItemSelectorWidget({
            el: $('#g-dialog-container'),
            parentView: this,
            model: this.model,
            rootPath: this._rootPath,
            rootSelectorSettings: {
                pageLimit: 1000
            }
        });
        modal.once('g:saved', () => {
            modal.$el.modal('hide');
        }).render();
    },

    _getDefaultOutputFolder() {
        const user = getCurrentUser();
        if (!user) {
            return $.Deferred().resolve(null).promise();
        }
        const userFolders = new FolderCollection();
        // find first private one
        return userFolders.fetch({
            parentId: user.id,
            parentType: 'user',
            public: false,
            limit: 1
        }).then(() => {
            if (!userFolders.isEmpty()) {
                return userFolders;
            }
            // find first one including public
            return userFolders.fetch({
                parentId: user.id,
                parentType: 'user',
                limit: 1
            });
        }).then(() => {
            return userFolders.isEmpty() ? null : userFolders.at(0);
        });
    },

    _getDefaultInputResource(model) {
        var type = {image: 'item', item: 'item', file: 'file', directory: 'folder'}[model.get('type')];
        return restRequest({
            url: 'slicer_cli_web/path_match',
            data: {
                type: type,
                name: model.get('defaultNameMatch'),
                path: model.get('defaultPathMatch')
            },
            error: null
        }).then((resource) => {
            var ModelType = {image: ItemModel, item: ItemModel, file: FileModel, directory: FolderModel}[model.get('type')];
            return new ModelType(resource);
        });
    },

    /**
     * Trigger a global event to initiate rectangle drawing mode to whoever
     * might be listening.
     */
    _selectRegion() {
        events.trigger('s:widgetDrawRegion', this.model);
    }
});

export default ControlWidget;
