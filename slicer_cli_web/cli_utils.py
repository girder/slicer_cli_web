"""utils for CLI spec handling."""
import six
import tempfile

from ctk_cli import CLIModule


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
