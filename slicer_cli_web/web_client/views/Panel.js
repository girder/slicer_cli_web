import $ from 'jquery';
import View from '@girder/core/views/View';

import panel from '../templates/panel.pug';
import '../stylesheets/panel.styl';

const Panel = View.extend({
    events: {
        'show.bs.collapse': 'expand',
        'hide.bs.collapse': 'collapse',
        'click .s-panel-title-container': '_handleTitleClick'
    },
    initialize(settings) {
        this.spec = settings.spec;
    },
    render() {
        this.$el.html(panel(this.spec));
        this.$('.s-panel-content').collapse({toggle: false});
        return this;
    },
    expand() {
        this.$('.icon-down-open').attr('class', 'icon-up-open');
    },
    collapse() {
        this.$('.icon-up-open').attr('class', 'icon-down-open');
    },
    _handleTitleClick(e) {
        if (!$(e.target).closest('.s-no-panel-toggle').length) {
            e.stopImmediatePropagation();
            this.$('.s-panel-content').collapse('toggle');
        }
    }
});

export default Panel;
