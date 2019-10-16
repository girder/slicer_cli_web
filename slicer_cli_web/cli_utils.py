"""utils for CLI spec handling."""
import six
import tempfile

from ctk_cli import CLIModule


return_parameter_file_name = 'returnparameterfile'

SLICER_TYPE_TO_GIRDER_MODEL_MAP = {
    'image': 'file',
    'file': 'file',
    'item': 'item',
    'directory': 'folder'
}

SLICER_SUPPORTED_TYPES = set(['boolean', 'integer', 'float', 'double', 'string',
                              'integer-vector', 'float-vector', 'double-vector', 'string-vector',
                              'integer-enumeration', 'float-enumeration', 'double-enumeration',
                              'string-enumeration',
                              'region'] + list(SLICER_TYPE_TO_GIRDER_MODEL_MAP.keys()))


def generate_description(clim):
    """Create CLI description string."""
    str_description = ['Description: <br/><br/>' + clim.description]

    if clim.version is not None and len(clim.version) > 0:
        str_description.append('Version: ' + clim.version)

    if clim.license is not None and len(clim.license) > 0:
        str_description.append('License: ' + clim.license)

    if clim.contributor is not None and len(clim.contributor) > 0:
        str_description.append('Author(s): ' + clim.contributor)

    if clim.acknowledgements is not None and len(clim.acknowledgements) > 0:
        str_description.append('Acknowledgements: ' + clim.acknowledgements)

    return '<br/><br/>'.join(str_description)


def as_model(cliXML):
    """Parses cli xml spec."""
    with tempfile.NamedTemporaryFile(suffix='.xml') as f:
        f.write(cliXML if isinstance(cliXML, six.binary_type) else cliXML.encode('utf8'))
        f.flush()
        return CLIModule(f.name)


def get_cli_parameters(clim):

    # get parameters
    index_params, opt_params, simple_out_params = clim.classifyParameters()

    # perform sanity checks
    for param in index_params + opt_params:
        if param.typ not in SLICER_SUPPORTED_TYPES:
            raise Exception(
                'Parameter type %s is currently not supported' % param.typ
            )

    # sort indexed parameters in increasing order of index
    index_params.sort(key=lambda p: p.index)

    # sort opt parameters in increasing order of name for easy lookup
    def get_flag(p):
        if p.flag is not None:
            return p.flag.strip('-')
        elif p.longflag is not None:
            return p.longflag.strip('-')
        else:
            return None

    opt_params.sort(key=lambda p: get_flag(p))

    return index_params, opt_params, simple_out_params


def is_on_girder(param):
    return param.typ in SLICER_TYPE_TO_GIRDER_MODEL_MAP
