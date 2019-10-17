import _ from 'underscore';

import { wrap } from '@girder/core/utilities/PluginUtils';
import View from '@girder/core/views/View';
import ItemView from '@girder/core/views/body/ItemView';
import WidgetCollection from '../collections/WidgetCollection';
import ControlsPanel from './ControlsPanel';
import { parse } from '../parser';
import slicerUI from '../templates/slicerUI.pug';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', function () {
        if (this.model.get('meta').slicerCLIType !== 'task') {
            return;
        }
        if (!this.model.parent || !this.model.parent.get('meta').slicerCLIRestPath) {
            return;
        }
        this.slicerCLIPanel = new SlicerUI({
            el: $('<form>', { class: 'g-item-slicer-ui' })
                .insertAfter(this.$('.g-item-info')),
            parentView: this,
            taskModel: this.model
        });
        this.slicerCLIPanel.render();
    });
    render.call(this);
});

const SlicerUI = View.extend({
    initialize(settings) {
        this.panels = [];
        this._panelViews = {};

        this.taskModel = settings.taskModel;
        this.restPath = `${this.taskModel.parent.get('meta').slicerCLIRestPath}/${this.taskModel.get('name')}`;

        this.loadModel();
    },

    render() {
        this.$el.html(slicerUI({
            panels: this.panels
        }));
        this.panels.forEach((panel) => {
            this._panelViews[panel.id] = new ControlsPanel({
                parentView: this,
                collection: new WidgetCollection(panel.parameters),
                title: panel.label,
                advanced: panel.advanced,
                el: this.$el.find(`#${panel.id}`)
            });
            this._panelViews[panel.id].render();
        });
    },

    loadModel() {
        const xml = this.taskModel.get('meta').xml;
        const opts = {};
        this.spec = parse(xml, opts);

        if (opts.outputs) {
            this._addParamFileOutput();
        }

        // Create a panel for each "group" in the schema, and copy
        // the advanced property from the parent panel.
        this.panels = [].concat(...this.spec.panels.map((panel) => {
            return panel.groups.map((group) => {
                group.advanced = !!panel.advanced;
                group.id = _.uniqueId('panel-');
                return group;
            });
        }));
    },

    _addParamFileOutput() {
        this.spec.panels.unshift({
            groups: [{
                label: 'Parameter outputs',
                parameters: [{
                    type: 'new-file',
                    slicerType: 'file',
                    id: 'returnparameterfile',
                    title: 'Parameter output file',
                    description: 'Output parameters returned by the analysis will be stored in this file.',
                    channel: 'output'
                }]
            }]
        });
    }
});