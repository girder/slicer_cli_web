import os

import pytest
from pytest_girder.web_client import runWebClientTest


@pytest.mark.plugin('slicer_cli_web')
@pytest.mark.parametrize('spec', (
    'configViewSpec.js',
    'containerViewSpec.js',
    'panelGroupSpec.js',
    'parseSpec.js',
    'widgetSpec.js',
    'itemSelectorWidgetSpec.js',
))
def testWebClient(boundServer, fsAssetstore, db, admin, spec):  # noqa
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)


@pytest.mark.usefixtures('girderWorker')
@pytest.mark.plugin('slicer_cli_web')
@pytest.mark.parametrize('spec', (
    'dockerTaskSpec.js',
))
def testWebClientWithWorker(boundServer, fsAssetstore, db, admin, spec, girderWorker):  # noqa
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)
