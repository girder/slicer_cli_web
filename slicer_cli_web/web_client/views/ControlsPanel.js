import Panel from './Panel';
import ControlWidget from './ControlWidget';

import controlsPanel from '../templates/controlsPanel.pug';
import '../stylesheets/controlsPanel.styl';

const ControlsPanel = Panel.extend({
    initialize(settings) {
        this._controlWidgetSettings = settings.controlWidget || {};

        this.title = settings.title || '';
        this.description = settings.description || '';
        this.advanced = settings.advanced || false;
        this.listenTo(this.collection, 'add', this.addOne);
        this.listenTo(this.collection, 'reset', this.render);
        this.listenTo(this.collection, 'remove', this.removeWidget);
    },

    render() {
        this.$el.html(controlsPanel({
            title: this.title,
            description: this.description,
            collapsed: this.advanced,
            id: this.$el.attr('id')
        }));
        this.addAll();
        this.$('.s-panel-content').collapse({toggle: false});
    },

    addOne(model) {
        const view = new ControlWidget(Object.assign({
            model: model,
            parentView: this
        }, this._controlWidgetSettings));
        this.$('form').append(view.render().el);
    },

    addAll() {
        this.$('form').children().remove();
        this.collection.each(this.addOne, this);
    },

    removeWidget(model) {
        model.destroy();
    }
});

export default ControlsPanel;
