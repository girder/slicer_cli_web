"""utils for CLI spec handling."""
import six
import tempfile

from ctk_cli import CLIModule


return_parameter_file_name = 'returnparameterfile'

SLICER_TO_GIRDER_WORKER_TYPE_MAP = {
    'boolean': 'boolean',
    'integer': 'integer',
    'float': 'number',
    'double': 'number',
    'string': 'string',
    'integer-vector': 'integer_list',
    'float-vector': 'number_list',
    'double-vector': 'number_list',
    'string-vector': 'string_list',
    'integer-enumeration': 'integer',
    'float-enumeration': 'number',
    'double-enumeration': 'number',
    'string-enumeration': 'string',
    'region': 'number_list',
    'file': 'string',
    'directory': 'string',
    'image': 'string'
}


SLICER_TYPE_TO_GIRDER_MODEL_MAP = {
    'image': 'file',
    'file': 'file',
    'item': 'item',
    'directory': 'folder'
}


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
        if param.typ not in SLICER_TO_GIRDER_WORKER_TYPE_MAP.keys():
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
