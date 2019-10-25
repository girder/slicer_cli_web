import six
from xml.etree.ElementTree import Element, SubElement, dump


def copy(parent, data, *keys, **kwargs):
    for key in keys:
        if key in data:
            SubElement(parent, key).text = str(data[key])

    for key, value in six.iteritems(kwargs):
        if key in data:
            SubElement(parent, value).text = str(data[key])


def copy_attr(parent, data, *keys, **kwargs):
    for key in keys:
        if key in data:
            parent.set(key, str(data[key]))

    for key, value in six.iteritems(kwargs):
        if key in data:
            parent.set(value, str(data[key]))


def convert_param(parent, param):
    p = SubElement(parent, param['type'])
    if param.get('multiple'):
        p.set('multiple', 'true')

    copy(p, param, 'label', 'description', 'name', 'index', 'channel')

    copy_attr(p, param, 'coordinateSystem', 'fileExtensions',
              image_type='type', table_type='type', geometry_type='type',
              transform_type='type')

    if 'default' in param:
        default_value = param['default']
        d = SubElement(p, 'default')
        if param['type'].endswith('-vector'):
            d.text = ','.join(str(v) for v in default_value)
        elif param['type'] == 'region':
            center = default_value['center']
            radius = default_value['radius']
            d.text = '%s,%s,%s,%s,%s,%s' % (
                center['x'], center['y'], center['z'], radius['x'], radius['y'], radius['z'])
        else:
            d.text = str(default_value)

    if 'enumeration' in param:
        for value in param['enumeration']:
            SubElement(p, 'element').text = str(value)

    if 'constraints' in param:
        c = SubElement(p, 'constraints')
        copy(c, param['constraints'], 'minimum', 'maximum', 'step')

    if 'reference' in param:
        ref = param['reference']
        if isinstance(ref, dict):
            ref_e = SubElement(p, 'reference')
            copy_attr(ref_e, ref, 'role', 'parameter')
            ref_e.text = ref['value']
        else:
            p.set('reference', ref)


def convert_group(parent, group):
    parameters = SubElement(parent, 'parameters')
    if group.get('advanced'):
        parameters.set('advanced', 'true')
    copy(parameters, group, 'label', 'description')

    if 'parameters' not in group:
        return

    for param in group['parameters']:
        convert_param(parameters, param)


def json_to_xml(data):
    root = Element('executable')
    copy(root, data, 'category', 'title', 'description', 'version', 'license',
         'contributor', 'documentation_url', 'acknowledgements')

    if 'parameter_groups' in data:
        for group in data['parameter_groups']:
            convert_group(root, group)

    return dump(root)