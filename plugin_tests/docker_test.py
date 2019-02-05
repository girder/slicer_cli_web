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

import docker
import json
import six
import threading
import types

from tests import base
from girder import events

# boiler plate to start and stop the server
TIMEOUT = 180


def setUpModule():
    base.enabledPlugins.append('slicer_cli_web')
    base.startServer()
    global JobStatus
    from girder.plugins.jobs.constants import JobStatus


def tearDownModule():
    base.stopServer()


class DockerImageManagementTest(base.TestCase):

    def setUp(self):
        # adding and removing docker images and using generated rest endpoints
        # requires admin access
        base.TestCase.setUp(self)
        admin = {
            'email': 'admin@email.com',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = self.model('user').createUser(**admin)

    def testAddNonExistentImage(self):
        # add a bad image
        img_name = 'null/null:null'
        self.assertNoImages()
        self.addImage(img_name, JobStatus.ERROR)
        self.assertNoImages()

    def testDockerAdd(self):
        # try to cache a good image to the mongo database
        img_name = 'girder/slicer_cli_web:small'
        self.assertNoImages()
        self.addImage(img_name, JobStatus.SUCCESS)
        self.imageIsLoaded(img_name, True)
        self.endpointsExist(img_name, ['Example1', 'Example2'], ['Example3'])

    def testDockerAddBadParam(self):
        # test sending bad parameters to the PUT endpoint
        kwargs = {
            'path': '/slicer_cli_web/slicer_cli_web/docker_image',
            'user': self.admin,
            'method': 'PUT',
            'params': {'name': json.dumps(6)}
        }
        resp = self.request(**kwargs)
        self.assertStatus(resp, 400)
        self.assertIn('A valid string', resp.json['message'])
        kwargs['params']['name'] = json.dumps({'abc': 'def'})
        resp = self.request(**kwargs)
        self.assertStatus(resp, 400)
        self.assertIn('A valid string', resp.json['message'])
        kwargs['params']['name'] = json.dumps([6])
        resp = self.request(**kwargs)
        self.assertStatus(resp, 400)
        self.assertIn('is not a valid string', resp.json['message'])
        kwargs['params']['name'] = '"not json'
        resp = self.request(**kwargs)
        self.assertStatus(resp, 400)
        self.assertIn('does not have a tag', resp.json['message'])

    def testDockerAddList(self):
        # try to cache a good image to the mongo database
        img_name = 'girder/slicer_cli_web:small'
        self.assertNoImages()
        self.addImage([img_name], JobStatus.SUCCESS)
        self.imageIsLoaded(img_name, True)

    def testDockerAddWithoutVersion(self):
        # all images need a version or hash
        img_name = 'girder/slicer_cli_web'
        self.assertNoImages()
        self.addImage(img_name, None, 400)
        self.assertNoImages()

    def testDockerDelete(self):
        # just delete the metadata in the mongo database
        # don't delete the docker image
        img_name = 'girder/slicer_cli_web:small'
        self.assertNoImages()
        self.addImage(img_name, JobStatus.SUCCESS)
        self.imageIsLoaded(img_name, True)
        self.deleteImage(img_name, True, False)
        self.imageIsLoaded(img_name, exists=False)
        self.assertNoImages()

    def testDockerDeleteFull(self):
        # attempt to delete docker image metadata and the image off the local
        # machine
        img_name = 'girder/slicer_cli_web:small'
        self.assertNoImages()
        self.addImage(img_name, JobStatus.SUCCESS)
        self.imageIsLoaded(img_name, True)
        self.deleteImage(img_name, True, True, JobStatus.SUCCESS)

        try:
            docker_client = docker.from_env(version='auto')
        except Exception as err:
            self.fail('could not create the docker client ' + str(err))

        try:
            docker_client.images.get(img_name)
            self.fail('If the image was deleted then an attempt to get it '
                      'should raise a docker exception')
        except Exception:
            pass

        self.imageIsLoaded(img_name, exists=False)
        self.assertNoImages()

    def testDockerPull(self):
        # test an instance when the image must be pulled
        # Forces the test image to be deleted
        self.testDockerDeleteFull()
        self.testDockerAdd()

    def testBadImageDelete(self):
        # attempt to delete a non existent image
        img_name = 'null/null:null'
        self.assertNoImages()
        self.deleteImage(img_name, False, )

    def testXmlEndpoint(self):
        # loads an image and attempts to run an arbitrary xml endpoint

        img_name = 'girder/slicer_cli_web:small'
        self.testDockerAdd()

        name, tag = self.splitName(img_name)
        data = self.getEndpoint()
        for (image, tag) in six.iteritems(data):
            for (version_name, cli) in six.iteritems(tag):
                for (cli_name, info) in six.iteritems(cli):
                    route = info['xmlspec']
                    resp = self.request(
                        path=route,
                        user=self.admin,
                        isJson=False)
                    self.assertStatus(resp, 200)
                    xmlString = self.getBody(resp)
                    # TODO validate with xml schema
                    self.assertNotEqual(xmlString, '')

    def testEndpointDeletion(self):
        img_name = 'girder/slicer_cli_web:small'
        self.testXmlEndpoint()
        data = self.getEndpoint()
        self.deleteImage(img_name, True)
        name, tag = self.splitName(img_name)

        for (image, tag) in six.iteritems(data):
            for (version_name, cli) in six.iteritems(tag):
                for (cli_name, info) in six.iteritems(cli):
                    route = info['xmlspec']
                    resp = self.request(
                        path=route,
                        user=self.admin,
                        isJson=False)
                    # xml route should have been deleted
                    self.assertStatus(resp, 400)

    def testAddBadImage(self):
        # job should fail gracefully after pulling the image
        img_name = 'library/hello-world:latest'
        self.assertNoImages()
        self.addImage(img_name, JobStatus.ERROR)
        self.assertNoImages()

    def splitName(self, name):
        if ':' in name:
            imageAndTag = name.split(':')
        else:
            imageAndTag = name.split('@')
        return imageAndTag[0], imageAndTag[1]

    def imageIsLoaded(self, name, exists):
        userAndRepo, tag = self.splitName(name)

        data = self.getEndpoint()
        if not exists:
            if userAndRepo in data:
                imgVersions = data[userAndRepo]
                self.assertNotHasKeys(imgVersions, [tag])

        else:
            self.assertHasKeys(data, [userAndRepo])
            imgVersions = data[userAndRepo]
            self.assertHasKeys(imgVersions, [tag])

    def endpointsExist(self, name, present=[], absent=[]):
        """
        Test if endpoints for particular image exist.

        :param name: name of the image used to determine endpoint location.
        :param present: a list of endpoints within the image that must exist.
        :param absent: a list of endpoints that should be in the image but not
            have endpoints.
        """
        userAndRepo, tag = self.splitName(name)
        data = self.getEndpoint()
        for cli in present:
            self.assertHasKeys(data, [userAndRepo])
            self.assertHasKeys(data[userAndRepo], [tag])
            self.assertHasKeys(data[userAndRepo][tag], [cli])
            path = data[userAndRepo][tag][cli]['xmlspec']
            resp = self.request(path=path, user=self.admin, isJson=False)
            self.assertStatusOk(resp)
        for cli in absent:
            self.assertHasKeys(data, [userAndRepo])
            self.assertHasKeys(data[userAndRepo], [tag])
            self.assertNotHasKeys(data[userAndRepo][tag], [cli])

    def getEndpoint(self):
        resp = self.request(path='/slicer_cli_web/slicer_cli_web/docker_image',
                            user=self.admin)
        self.assertStatus(resp, 200)
        return json.loads(self.getBody(resp))

    def assertNoImages(self):
        data = self.getEndpoint()
        self.assertEqual({}, data,
                         'There should be no pre existing docker images')

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
                    self.assertEqual(job['status'], status,
                                     'The status of the job should match')
                    events.unbind('jobs.job.update.after', 'slicer_cli_web_del')
                    job_status[0] = job['status']
                    event.set()

            self.delHandler = types.MethodType(tempListener, self)

            events.bind('jobs.job.update.after', 'slicer_cli_web_del',
                        self.delHandler)

        resp = self.request(path='/slicer_cli_web/slicer_cli_web/docker_image',
                            user=self.admin, method='DELETE',
                            params={'name': json.dumps(name),
                                    'delete_from_local_repo':
                                        deleteDockerImage
                                    }, isJson=False)
        if responseCodeOK:
            self.assertStatus(resp, 200)
        else:
            try:
                self.assertStatus(resp, 200)
                self.fail('A status ok or code 200 should not have been '
                          'recieved for deleting the image %s' % str(name))
            except Exception:
                pass
        if deleteDockerImage:
            if not event.wait(TIMEOUT):
                del self.delHandler
                self.fail('deleting the docker image is taking '
                          'longer than %d seconds' % TIMEOUT)
            else:
                del self.delHandler
                self.assertEqual(job_status[0], status,
                                 'The status of the job should match ')

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
                self.assertEqual(job['status'], status,
                                 'The status of the job should match')
                job_status[0] = job['status']

                events.unbind('jobs.job.update.after', 'slicer_cli_web_add')

                event.set()

        if initialStatus == 200:
            self.addHandler = types.MethodType(tempListener, self)

            events.bind('jobs.job.update.after',
                        'slicer_cli_web_add', self.addHandler)

        resp = self.request(
            path='/slicer_cli_web/slicer_cli_web/docker_image',
            user=self.admin, method='PUT', params={'name': json.dumps(name)},
            isJson=initialStatus == 200)

        self.assertStatus(resp, initialStatus)
        if initialStatus != 200:
            return
        # We should have a job ID
        self.assertIsNotNone(resp.json.get('_id'))

        if not event.wait(TIMEOUT):
            del self.addHandler
            self.fail('adding the docker image is taking longer than %d seconds' % TIMEOUT)
        else:
            del self.addHandler
            self.assertEqual(job_status[0], status,
                             'The status of the job should match ')
