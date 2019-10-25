import jsonschema
import yaml

from girder.models.file import File
from ..cli_utils import as_model


def parse_xml_desc(item, desc, user):
    meta_data = {
        'xml': desc['xml']
    }

    # parse and inject advanced meta data and description
    clim = as_model(desc['xml'])
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


def parse_yaml_desc(item, desc, user):
    meta_data = {
        'yaml': desc['yaml']
    }

    desc = yaml.safe_load(desc['yaml'])
    jsonschema.validate(desc, )
    # TODO
    return meta_data
