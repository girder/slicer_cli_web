#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import pytest
import docker
import json
import six
import threading
import types

from girder import events
from girder_jobs.constants import JobStatus
from pytest_girder.assertions import assertStatus, assertStatusOk
from pytest_girder.utils import getResponseBody

# boiler plate to start and stop the server
TIMEOUT = 180


def splitName(name):
    if ':' in name:
        imageAndTag = name.split(':')
    else:
        imageAndTag = name.split('@')
    return imageAndTag[0], imageAndTag[1]


class ImageHelper(object):
    def __init__(self, server, admin, folder):
        self.server = server
        self.admin = admin
        self.folder = folder

    def assertHasKeys(self, obj, keys):
        for key in keys:
            assert key in obj

    def assertNotHasKeys(self, obj, keys):
        for key in keys:
            assert key not in obj

    def getEndpoint(self):
        resp = self.server.request(path='/slicer_cli_web/docker_image',
                                   user=self.admin)
        assertStatus(resp, 200)

        return json.loads(getResponseBody(resp))

    def assertNoImages(self):
        data = self.getEndpoint()
        assert {} == data, 'There should be no pre existing docker images'

    def imageIsLoaded(self, name, exists):
        userAndRepo, tag = splitName(name)

        data = self.getEndpoint()
        if not exists:
            if userAndRepo in data:
                imgVersions = data[userAndRepo]
                self.assertNotHasKeys(imgVersions, [tag])
        else:
            self.assertHasKeys(data, [userAndRepo])
            imgVersions = data[userAndRepo]
            self.assertHasKeys(imgVersions, [tag])

    def endpointsExist(self, name, present=None, absent=None):
        """
        Test if endpoints for particular image exist.

        :param name: name of the image used to determine endpoint location.
        :param present: a list of endpoints within the image that must exist.
        :param absent: a list of endpoints that should be in the image but not
            have endpoints.
        """
        present = present or []
        absent = absent or []
        userAndRepo, tag = splitName(name)
        data = self.getEndpoint()
        for cli in present:
            self.assertHasKeys(data, [userAndRepo])
            self.assertHasKeys(data[userAndRepo], [tag])
            self.assertHasKeys(data[userAndRepo][tag], [cli])
            path = data[userAndRepo][tag][cli]['xmlspec']
            resp = self.server.request(path=path, user=self.admin, isJson=False)
            assertStatusOk(resp)
        for cli in absent:
            self.assertHasKeys(data, [userAndRepo])
            self.assertHasKeys(data[userAndRepo], [tag])
            self.assertNotHasKeys(data[userAndRepo][tag], [cli])

    def deleteImage(self, name, responseCodeOK, deleteDockerImage=False,
                    status=4):
        """
        Delete docker image data and test whether a docker
        image can be deleted off the local machine
        """
        job_status = [JobStatus.SUCCESS]
        if deleteDockerImage:
            event = threading.Event()

            def tempListener(self, girderEvent):
                job = girderEvent.info['job']

                if (job['type'] == 'slicer_cli_web_job' and
                        job['status'] in (JobStatus.SUCCESS, JobStatus.ERROR)):
                    assert job['status'] == status, 'The status of the job should match'
                    events.unbind('jobs.job.update.after', 'slicer_cli_web_del')
                    job_status[0] = job['status']
                    event.set()

            self.delHandler = types.MethodType(tempListener, self)

            events.bind('jobs.job.update.after', 'slicer_cli_web_del',
                        self.delHandler)

        resp = self.server.request(path='/slicer_cli_web/docker_image',
                                   user=self.admin, method='DELETE',
                                   params={'name': json.dumps(name),
                                           'delete_from_local_repo':
                                               deleteDockerImage
                                           }, isJson=False)
        if responseCodeOK:
            assertStatus(resp, 200)
        else:
            assertStatus(resp, 400)
            # A status ok or code 200 should not have been recieved for
            # deleting the image %s' % str(name))

        if deleteDockerImage:
            if not event.wait(TIMEOUT):
                del self.delHandler
                raise AssertionError('deleting the docker image is taking '
                                     'longer than %d seconds' % TIMEOUT)
            else:
                del self.delHandler
                assert job_status[0] == status, 'The status of the job should match '

    def addImage(self, name, status, initialStatus=200):
        """
        Test the put endpoint.

        :param name: a string or a list of strings
        :param status: either JobStatus.SUCCESS or JobStatus.ERROR.
        :param initialStatus: 200 if the job should run, otherwise a HTTP error
            code expected if the job will fail.
        """
        event = threading.Event()
        job_status = [JobStatus.SUCCESS]

        def tempListener(self, girderEvent):
            job = girderEvent.info['job']

            if (job['type'] == 'slicer_cli_web_job' and
                    job['status'] in (JobStatus.SUCCESS, JobStatus.ERROR)):
                assert job['status'] == status, 'The status of the job should match'
                job_status[0] = job['status']

                events.unbind('jobs.job.update.after', 'slicer_cli_web_add')

                # wait 10sec before continue
                threading.Timer(5, lambda: event.set()).start()

        if initialStatus == 200:
            self.addHandler = types.MethodType(tempListener, self)

            events.bind('jobs.job.update.after',
                        'slicer_cli_web_add', self.addHandler)

        resp = self.server.request(
            path='/slicer_cli_web/docker_image',
            user=self.admin, method='PUT', params={'name': json.dumps(name),
                                                   'folder': self.folder['_id']},
            isJson=initialStatus == 200)

        assertStatus(resp, initialStatus)
        if initialStatus != 200:
            return
        # We should have a job ID
        assert resp.json.get('_id') is not None

        if not event.wait(TIMEOUT):
            del self.addHandler
            raise AssertionError('adding the docker image is taking '
                                 'longer than %d seconds' % TIMEOUT)
        else:
            del self.addHandler
            job_status[0] == status, 'The status of the job should match '


@pytest.fixture
def images(server, admin, folder):
    return ImageHelper(server, admin, folder)


@pytest.mark.plugin('slicer_cli_web')
def testAddNonExistentImage(images):
    # add a bad image
    img_name = 'null/null:null'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.ERROR)
    images.assertNoImages()


@pytest.mark.plugin('slicer_cli_web')
def testDockerAdd(images, server):
    # try to cache a good image to the mongo database
    img_name = 'girder/slicer_cli_web:small'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    # If checked without a user, we should get an empty list
    resp = server.request(path='/slicer_cli_web/docker_image')
    assertStatus(resp, 200)
    assert json.loads(getResponseBody(resp)) == {}
    images.endpointsExist(img_name, ['Example1', 'Example2', 'Example3'], ['NotAnExample'])
    images.deleteImage(img_name, True)
    images.assertNoImages()


@pytest.mark.plugin('slicer_cli_web')
def testDockerAddBadParam(server, admin, folder):
    # test sending bad parameters to the PUT endpoint
    kwargs = {
        'path': '/slicer_cli_web/docker_image',
        'user': admin,
        'method': 'PUT',
        'params': {'name': json.dumps(6), 'folder': folder['_id']}
    }
    resp = server.request(**kwargs)
    assertStatus(resp, 400)
    assert 'A valid string' in resp.json['message']

    kwargs['params']['name'] = json.dumps({'abc': 'def'})
    resp = server.request(**kwargs)
    assertStatus(resp, 400)
    assert 'A valid string' in resp.json['message']

    kwargs['params']['name'] = json.dumps([6])
    resp = server.request(**kwargs)
    assertStatus(resp, 400)
    assert 'is not a valid string' in resp.json['message']

    kwargs['params']['name'] = '"not json'
    resp = server.request(**kwargs)
    assertStatus(resp, 400)
    assert 'does not have a tag' in resp.json['message']


@pytest.mark.plugin('slicer_cli_web')
def testDockerAddList(images):
    # try to cache a good image to the mongo database
    img_name = 'girder/slicer_cli_web:small'
    images.assertNoImages()
    images.addImage([img_name], JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    images.deleteImage(img_name, True)
    images.assertNoImages()


@pytest.mark.plugin('slicer_cli_web')
def testDockerAddWithoutVersion(images):
    # all images need a version or hash
    img_name = 'girder/slicer_cli_web'
    images.assertNoImages()
    images.addImage(img_name, None, 400)
    images.assertNoImages()


@pytest.mark.plugin('slicer_cli_web')
def testDockerDelete(images):
    # just delete the metadata in the mongo database
    # don't delete the docker image
    img_name = 'girder/slicer_cli_web:small'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    images.deleteImage(img_name, True, False)
    images.imageIsLoaded(img_name, exists=False)
    images.assertNoImages()


@pytest.mark.plugin('slicer_cli_web')
def testDockerDeleteFull(images):
    # attempt to delete docker image metadata and the image off the local
    # machine
    img_name = 'girder/slicer_cli_web:small'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    images.deleteImage(img_name, True, True, JobStatus.SUCCESS)

    try:
        docker_client = docker.from_env(version='auto')
    except Exception as err:
        raise AssertionError('could not create the docker client ' + str(err))

    try:
        docker_client.images.get(img_name)
        raise AssertionError('If the image was deleted then an attempt to get it '
                             'should raise a docker exception')
    except Exception:
        pass

    images.imageIsLoaded(img_name, exists=False)
    images.assertNoImages()


@pytest.mark.plugin('slicer_cli_web')
def testBadImageDelete(images):
    # attempt to delete a non existent image
    img_name = 'null/null:null'
    images.assertNoImages()
    images.deleteImage(img_name, False, )


@pytest.mark.plugin('slicer_cli_web')
def testXmlEndpoint(images, server, admin):
    # loads an image and attempts to run an arbitrary xml endpoint

    img_name = 'girder/slicer_cli_web:small'
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)

    name, tag = splitName(img_name)
    data = images.getEndpoint()
    for tag in six.itervalues(data):
        for cli in six.itervalues(tag):
            for info in six.itervalues(cli):
                route = info['xmlspec']
                resp = server.request(
                    path=route,
                    user=admin,
                    isJson=False)
                assertStatus(resp, 200)
                xmlString = getResponseBody(resp)
                # TODO validate with xml schema
                assert xmlString != ''
    images.deleteImage(img_name, True, )


@pytest.mark.plugin('slicer_cli_web')
def testEndpointDeletion(images, server, admin):
    img_name = 'girder/slicer_cli_web:small'
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    data = images.getEndpoint()
    images.deleteImage(img_name, True)
    name, tag = splitName(img_name)

    for tag in six.itervalues(data):
        for cli in six.itervalues(tag):
            for info in six.itervalues(cli):
                route = info['xmlspec']
                resp = server.request(
                    path=route,
                    user=admin,
                    isJson=False)
                # xml route should have been deleted
                assertStatus(resp, 400)


@pytest.mark.plugin('slicer_cli_web')
def testAddBadImage(images):
    # job should fail gracefully after pulling the image
    img_name = 'library/hello-world:latest'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.ERROR)
    images.assertNoImages()
