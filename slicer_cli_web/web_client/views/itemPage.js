import _ from 'underscore';

import { wrap } from '@girder/core/utilities/PluginUtils';
import { restRequest } from '@girder/core/rest';
import View from '@girder/core/views/View';
import ItemView from '@girder/core/views/body/ItemView';
import WidgetCollection from '../collections/WidgetCollection';
import ControlsPanel from './ControlsPanel';
import PanelGroup from './PanelGroup';
import { parse } from '../parser';
import slicerUI from '../templates/slicerUI.pug';
import '../stylesheets/slicerUI.styl';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', function () {
        if (this.model.get('meta').slicerCLIType !== 'task') {
            return;
        }
        if (!this.model.parent || !this.model.parent.get('meta').slicerCLIRestPath) {
            return;
        }
        this.slicerCLIPanel = new SlicerUI({
            el: $('<div>', { class: 'g-item-slicer-ui' })
                .insertAfter(this.$('.g-item-info')),
            parentView: this,
            taskModel: this.model
        });
        this.slicerCLIPanel.render();
    });
    render.call(this);
});

const SlicerUI = View.extend({
    events: {
        'click .s-info-panel-submit': 'submit',
    },
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
                disableRegionSelect: true,
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
    },

    generateParameters() {
        return PanelGroup.prototype.parameters.call(this);
    },

    validate() {
        const invalidModels = PanelGroup.prototype.models.call(this, undefined, (m) => {
            return !m.isValid();
        });
        const alert = this.$('.s-validation-alert');
        alert.toggleClass('hidden', invalidModels.length === 0);
        alert.text(`Validation errors occurred for: ${invalidModels.map((d) => d.get('title')).join(', ')}`);

        return invalidModels.length === 0;
    },


    submit() {
        if (!this.validate()) {
            return;
        }
        const params = this.generateParameters();
        _.each(params, (value, key) => {
            if (Array.isArray(value)) {
                params[key] = JSON.stringify(value);
            }
        });

        // post the job to the server
        restRequest({
            url: `slicer_cli_web/${this.restPath}/run`,
            method: 'POST',
            data: params
        }).then((data) => {
            this.showSuccess(data);
            return null;
        });
    },

    showSuccess(job) {
        // manual alert since the default doesn't support HTML body
        const el = $(`
        <div class="alert alert-dismissable alert-success">
            <button class="close" type="button" data-dismiss="alert" aria-hidden="true"> &times; </button>
            <i class="icon-ok"></i>
            <strong>Job submitted</strong>. <br>
            Check the <a href="/#job/${job._id}" class="alert-link">Job status</a>.
        </div>`);
        $('#g-alerts-container').append(el);
        el.fadeIn(500);
    }
});