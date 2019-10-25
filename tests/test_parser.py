import pytest
import re

from slicer_cli_web.models.parser import parse_xml_desc, parse_json_desc, parse_yaml_desc


def assert_string_equal(a, b):
    """
    assert equal ignoring withspaces

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
</executable>"""

    json = """{
    "$schema": "../../slicer_cli_web/models/schema.json",
    "category": "A",
    "title": "T",
    "description": "D",
    "parameter_groups": []
}"""

    yaml = """category: A
title: T
description: D
parameter_groups: []
"""

    def test_xml(self, admin, item):
        meta = parse_xml_desc(item, dict(xml=TestParserSimple.xml), admin)
        assert_string_equal(meta.get('xml'), TestParserSimple.xml)
        assert meta.get('category') == 'A'
        assert item.get('description') == '**T**\n\nD'

    def test_json(self, admin, item):
        meta = parse_json_desc(item, dict(json=TestParserSimple.json), admin)
        assert_string_equal(meta.get('xml'), TestParserSimple.xml)
        assert meta.get('category') == 'A'
        assert item.get('description') == '**T**\n\nD'

    def test_yaml(self, admin, item):
        meta = parse_yaml_desc(item, dict(yaml=TestParserSimple.yaml), admin)
        assert_string_equal(meta.get('xml'), TestParserSimple.xml)
        assert meta.get('category') == 'A'
        assert item.get('description') == '**T**\n\nD'
