import _ from 'underscore';

import group from './group';

/**
 * Parse a <parameters> tag into a "panel" object.
 */
function panel(panelTag, opts = {}) {
    var $panel = $(panelTag);
    var groups = _.filter(
        _.map($panel.find('parameters > label'), (g) => group(g, opts)),
        _.isObject
    );

    if (!groups.length) {
        return null;
    }

    return {
        advanced: $panel.attr('advanced') === 'true',
        groups
    };
}

export default panel;
