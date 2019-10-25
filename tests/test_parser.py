import pytest
import re
import os

from slicer_cli_web.models.parser import parse_xml_desc, parse_json_desc, parse_yaml_desc


def read_file(name):
    with open(os.path.join(os.path.dirname(__file__), 'data', name)) as f:
        return f.read()


def assert_string_equal(a, b):
    """
    Assert equal ignoring withspaces

    """
    if a == b:
        return
    assert (a is None) == (b is None)
    if a is None:
        return

    white = re.compile('\\s+')

    a_clean = white.sub(a, '')
    b_clean = white.sub(b, '')

    assert a_clean == b_clean


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
class TestParserSimple:
    xml = read_file('parser_simple.xml')
    json = read_file('parser_simple.json')
    yaml = read_file('parser_simple.yaml')

    def verify(self, meta, item):
        from girder.models.item import Item

        assert_string_equal(meta.get('xml'), TestParserSimple.xml)
        assert meta.get('category') == 'A'
        assert meta.get('version') == 'V'
        assert meta.get('license') == 'L'
        assert meta.get('contributor') == 'C'
        assert meta.get('acknowledgements') == 'A'

        assert item.get('description') == '**T**\n\nD'

        files = list(Item().childFiles(item))
        assert len(files) == 1
        link = files[0]
        assert link['name'] == 'Documentation'
        assert link['linkUrl'] == 'https://github.com'

    def test_xml(self, admin, item):
        meta = parse_xml_desc(item, dict(xml=TestParserSimple.xml), admin)
        self.verify(meta, item)

    def test_json(self, admin, item):
        meta = parse_json_desc(item, dict(json=TestParserSimple.json), admin)
        self.verify(meta, item)

    def test_yaml(self, admin, item):
        meta = parse_yaml_desc(item, dict(yaml=TestParserSimple.yaml), admin)
        self.verify(meta, item)


@pytest.mark.plugin('slicer_cli_web')
class TestParserParamsSimple:
    xml = read_file('parser_params_simple.xml')
    json = read_file('parser_params_simple.json')
    yaml = read_file('parser_params_simple.yaml')

    def verify(self, meta, item):
        assert_string_equal(meta.get('xml'), TestParserParamsSimple.xml)

    def test_xml(self, admin, item):
        meta = parse_xml_desc(item, dict(xml=TestParserParamsSimple.xml), admin)
        self.verify(meta, item)

    def test_json(self, admin, item):
        meta = parse_json_desc(item, dict(json=TestParserParamsSimple.json), admin)
        self.verify(meta, item)

    def test_yaml(self, admin, item):
        meta = parse_yaml_desc(item, dict(yaml=TestParserParamsSimple.yaml), admin)
        self.verify(meta, item)
