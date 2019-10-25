import pytest


@pytest.fixture
def folder(admin):
    from girder.models.folder import Folder
    f = Folder().createFolder(admin, 'folder', parentType='user')

    yield f


@pytest.fixture
def item(folder, admin):
    from girder.models.item import Item
    f = Item().createItem('item', admin, folder)

    yield f


@pytest.mark.plugin('slicer_cli_web')
def test_xml_parser(admin, item):  # noqa
    from slicer_cli_web.models.parser import parse_xml_desc

    xml = """
<?xml version="1.0" encoding="UTF-8"?>
<executable>
  <category>A</category>
  <title>T</title>
  <description>D</description>
</executable>
"""

    meta = parse_xml_desc(item, dict(xml=xml), admin)
    assert meta.get('xml') == xml
    assert meta.get('category') == 'A'
    assert meta.get('title') == 'T'
    assert meta.get('description') == 'D'
