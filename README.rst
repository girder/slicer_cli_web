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

The first time you start Girder, you'll need to configure it with at least one user and one assetstore (see the Girder_ documentation).  Additionally, it is recommended that you install some dockerized tasks, such as the HistomicsTK_ algorithms.  This can be done going to the Admin Console, Plugins, Slicer CLI Web settings.  Set a default task upload folder, then import the `dsarchive/histomicstk:latest` docker image.

Girder Plugin
-------------

Importing Docker Images
=======================

When installed in Girder, an admin user can go to the Admin Console -> Plugins -> Slicer CLI Web to add Docker images.  Select a Docker image and an existing folder and then select Import Image.  Slicer CLI Web will pull the Docker image if it is not available on the Girder machine. 

For each docker image that is imported, a folder is created with the image tag.  Within this folder, a subfolder is created with the image version.  The subfolder will have one item per CLI that the Docker image reports.  These items can be moved after they have been imported, just like standard Girder items.

Running CLIs
============

When you visit the item page of an imported CLI, an extra ``Configure Task`` section is shown.  You can set all of the inputs for the CLI and indicate where output files should be stored.  Selecting ``Run Task`` will have Girder Worker execute the CLI.  See the Jobs panel for progress and error messages.

Docker CLIs
-----------

Slicer CLI Web executes programs from docker images.  Any docker image can be used that complies with some basic responses from its ``ENTRYPOINT``.

Specifically, when a docker image is invoked like::

    docker run <docker image tag> --list_cli

it needs to respond with with a JSON dictionary of CLIs, where the keys of this dictionary are the names of the CLIs.  See `cli_list.json <./small-docker/cli_list.json>`_ for an example.

Each available CLI needs to report what it takes as inputs and outputs.  When the docker image is invoked like::

    docker run <docker image tag> <cli name> --xml

it needs to return an XML specification to stdout.  See `Example1.xml <./small-docker/Example1/Example1.xml>`_ for an example.

The XML must conform to the `Slicer Execution Schema <https://www.slicer.org/w/index.php?title=Documentation/Nightly/Developers/SlicerExecutionModel>`_, with a few minor additions:

- Some types (``image``, ``file``, ``transform``, ``geometry``, ``table``) can have a ``reference`` property.

- The ``region`` type can have a ``coordinateSystem`` property.

- Some input types (``image``, ``file``, ``item``, ``directory``) can have ``defaultNameMatch`` and ``defaultPathMatch`` properties.  These are regular expressions designed to give a UI a value to match to prepopulate default values from files or paths that match the regex.  ``defaultNameMatch`` is intended to match the final path element, whereas ``defaultPathMatch`` is used on the entire path as a combined string.

- There are some special string parameters that, if unspecified or blank, are autopopulated.  String parameters with the names of ``girderApiUrl`` and ``girderToken`` are populated with the appropriate url and token so that a running job could use girder_client to communicate with Girder.


Small Example CLI Docker
========================

The small example CLI docker image can be built locally via ``docker build --force-rm -t girder/slicer_cli_web:small .``, or pulled from Docker Hub.


.. |build-status| image:: https://circleci.com/gh/girder/slicer_cli_web.svg?style=svg
    :target: https://circleci.com/gh/girder/slicer_cli_web
    :alt: Build Status

.. |codecov-io| image:: https://codecov.io/github/girder/slicer_cli_web/coverage.svg?branch=master
    :target: https://codecov.io/github/girder/slicer_cli_web?branch=master
    :alt: codecov.io

.. _Girder: http://girder.readthedocs.io/en/latest/
.. _Girder Worker: https://girder-worker.readthedocs.io/en/latest/
.. _HistomicsTK: https://github.com/DigitalSlideArchive/HistomicsTK

