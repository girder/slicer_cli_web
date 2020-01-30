==========================================
Slicer CLI Web |build-status| |codecov-io|
==========================================

A Girder plugin for exposing slicer execution model CLIs over the web using docker and girder_worker.

Installation
------------

Slicer CLI Web is both a Girder_ plugin and a `Girder Worker`_ plugin.  It allows dockerized tasks to be run from the Girder user interface.

Linux
=====

In linux with Python 2.7, Python 3.5, 3.6, or 3.7:

Prerequisites:

- An appropriate version of Python must be installed.
- MongoDB must be installed and running.
- RabbitMQ or another broker is needed to use Girder Worker.
- Docker must be installed and the current user must be part of the docker group.

To use Girder:

.. code-block:: bash

  pip install girder-slicer-cli-web[girder]
  girder build
  girder serve

To use Girder Worker:

.. code-block:: bash

  pip install girder-slicer-cli-web[worker]
  GW_DIRECT_PATHS=true girder_worker -l info -Ofair --prefetch-multiplier=1

The first time you start Girder, you'll need to configure it with at least one user and one assetstore (see the Girder_ documentation).  Additionally, it is recommended that you install some dockerized taskss, such as the HistomicsTK_ algorithms.  This can be done going to the Admin Console, Plugins, Slicer CLI Web settings.  Set a default task upload folder, then import the `dsarchive/histomicstk:latest` docker image.

.. |build-status| image:: https://circleci.com/gh/girder/slicer_cli_web.svg?style=svg
    :target: https://circleci.com/gh/girder/slicer_cli_web
    :alt: Build Status

.. |codecov-io| image:: https://codecov.io/github/girder/slicer_cli_web/coverage.svg?branch=master
    :target: https://codecov.io/github/girder/slicer_cli_web?branch=master
    :alt: codecov.io

.. _Girder: http://girder.readthedocs.io/en/latest/
.. _Girder Worker: https://girder-worker.readthedocs.io/en/latest/
.. _HistomicsTK: https://github.com/DigitalSlideArchive/HistomicsTK

