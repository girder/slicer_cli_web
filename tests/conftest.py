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


@pytest.fixture
def file(item, admin, fsAssetstore):
    from girder.models.file import File
    f = File().createFile(admin, item, 'file', 7, fsAssetstore)

    yield f
