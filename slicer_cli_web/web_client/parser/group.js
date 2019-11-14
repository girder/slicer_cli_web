import $ from 'jquery';
import _ from 'underscore';

import param from './param';

/**
 * Parse a parameter group (deliminated by <label> tags) within a
 * panel.
 */
export default function group(label, opts = {}) {
    // parameter groups inside panels
    const $label = $(label);
    const $description = $label.next('description');
    const parameters = _.filter(
        _.map($description.nextUntil('label'), (p) => param(p, opts)),
        _.isObject
    );

    // don't add the panel if there are no input parameters
    if (parameters.length === 0) {
        return null;
    }

    return {
        label: $label.text(),
        description: $description.text(),
        parameters
    };
}
