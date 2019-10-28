import pytest
import six


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
def file(folder, admin, fsAssetstore):
    from girder.models.upload import Upload
    sampleData = b'Hello world'
    f = Upload().uploadFromFile(
        obj=six.BytesIO(sampleData), size=len(sampleData), name='Sample',
        parentType='folder', parent=folder, user=admin)

    yield f


@pytest.fixture
def adminToken(admin):
    from girder.models.token import Token
    yield Token().createToken(admin)
