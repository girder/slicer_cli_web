import $ from 'jquery';
import _ from 'underscore';

import group from './group';

/**
 * Parse a <parameters> tag into a "panel" object.
 */
export default function panel(panelTag, opts = {}) {
    const $panel = $(panelTag);
    const groups = _.filter(
        _.map($panel.find('parameters > label'), (g) => group(g, opts)),
        _.isObject
    );

    if (groups.length === 0) {
        return null;
    }

    return {
        advanced: $panel.attr('advanced') === 'true',
        groups
    };
}
