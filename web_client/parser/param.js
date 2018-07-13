import _ from 'underscore';

import widget from './widget';
import convert from './convert';
import defaultValue from './defaultValue';
import constraints from './constraints';

/**
 * Parse a parameter spec.
 * @param {XML} param The parameter spec
 * @returns {object}
 */
function param(paramTag, opts = {}) {
    var $param = $(paramTag);
    var type = widget(paramTag);
    var values = {};
    var channel = $param.find('channel');
    var id = $param.find('name').text() || $param.find('longflag').text();
    var extra = {};

    if (channel.length) {
        channel = channel.text();
    } else {
        channel = 'input';
    }

    if ((type === 'file' || type === 'image') && channel === 'output') {
        type = 'new-file';
        extra['extensions'] = $param.attr('fileExtensions');
        extra['required'] = $param.find('index').text().length > 0;
    } else if (channel === 'output') {
        opts.output = true;
        opts.params = _.extend(opts.params || {}, {
            [id]: type
        });
        return null;
    }

    if (!type) {
        console.warn('Unhandled parameter type "' + paramTag.tagName + '"'); // eslint-disable-line no-console
    }

    if (type === 'string-enumeration' || type === 'number-enumeration') {
        values = {
            values: _.map($param.find('element'), (el) => {
                return convert(type, $(el).text());
            })
        };
    }

    return _.extend(
        {
            type: type,
            slicerType: paramTag.tagName,
            title: $param.find('label').text(),
            description: $param.find('description').text(),
            channel,
            id
        },
        values,
        defaultValue(type, $param.find('default')),
        constraints(type, $param.find('constraints').get(0)),
        extra
    );
}

export default param;
