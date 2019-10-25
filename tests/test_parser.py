import pytest
import re

from slicer_cli_web.models.parser import parse_xml_desc, parse_json_desc, parse_yaml_desc


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
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<executable>
  <category>A</category>
  <title>T</title>
  <description>D</description>
  <version>V</version>
  <license>L</license>
  <contributor>C</contributor>
  <acknowledgements>A</acknowledgements>
  <documentation-url>https://github.com</documentation-url>
</executable>"""

    json = """{
    "$schema": "../../slicer_cli_web/models/schema.json",
    "category": "A",
    "title": "T",
    "description": "D",
    "version": "V",
    "license": "L",
    "contributor": "C",
    "acknowledgements": "A",
    "documentation_url": "https://github.com",
    "parameter_groups": []
}"""

    yaml = """category: A
title: T
description: D
version: V
license: L
contributor: C
acknowledgements: A
documentation_url: https://github.com
parameter_groups: []
"""

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
