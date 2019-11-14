import convert from './convert';

/**
 * Parse a `default` tag returning an empty object when no default is given.
 */
export default function defaultValue(type, value) {
    if (value.length > 0) {
        return {value: convert(type, value.text())};
    }
    return {};
}
