import json
from jsonschema import validate
from os.path import join, dirname
import yaml


from girder.models.file import File
from ..cli_utils import as_model
from .json_to_xml import json_to_xml


with open(join(dirname(__file__), 'schema.json')) as f:
    json_schema = json.load(f)


def _parse_xml_desc(item, user, xml):
    meta_data = {
        'xml': xml
    }

    # parse and inject advanced meta data and description
    clim = as_model(xml)
    item['description'] = '**%s**\n\n%s' % (clim.title, clim.description)

    if clim.category:
        meta_data['category'] = clim.category
    if clim.version:
        meta_data['version'] = clim.version
    if clim.license:
        meta_data['license'] = clim.license
    if clim.contributor:
        meta_data['contributor'] = clim.contributor
    if clim.acknowledgements:
        meta_data['acknowledgements'] = clim.acknowledgements

    if clim.documentation_url:
        fileModel = File()
        fileModel.createLinkFile('Documentation', item, 'item',
                                 clim.documentation_url,
                                 user, reuseExisting=True)
    return meta_data


def parse_xml_desc(item, desc, user):
    return _parse_xml_desc(item, user, desc['xml'])


def _parse_json_desc(item, user, data):
    validate(data, schema=json_schema)
    xml = json_to_xml(data)
    return _parse_xml_desc(item, user, xml)


def parse_json_desc(item, desc, user):
    data = json.loads(desc['json'])

    return _parse_json_desc(item, user, data)


def parse_yaml_desc(item, desc, user):
    data = yaml.safe_load(desc['yaml'])

    return _parse_json_desc(item, user, data)
