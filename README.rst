==========================================
Slicer CLI Web |build-status| |codecov-io|
==========================================

A Girder plugin for exposing slicer execution model CLIs over the web using docker and girder_worker.

Installation
------------

Slicer CLI Web is both a Girder_ plugin and a `Girder Worker`_ plugin.  It allows dockerized tasks to be run from the Girder user interface.

Linux
=====

In linux with Python 3.6, 3.7, 3.8, or 3.9:

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

CLI Endpoints
=============

Each exposed CLI is added as an endpoint using the REST path of ``slicer_cli_web/<docker image tag and version>/<cli command>/run`` and also using the REST path of ``slicer_cli_web/<internal item id>/run``, where ``<docker image tag and version>`` is the combined tag and version with slashes, colons, and at signs replaced by underscores.  All command line parameters can be passed as endpoint query parameters.  Input items, folders, and files are specified by their Girder ID.  Input images are specified by a Girder file ID.  Output files are specified by name and with an associated parameter with the same name plus a ``_folder`` suffix with a Girder folder ID.

Small Example CLI Docker
========================

The small example CLI docker image can be built locally via ``docker build --force-rm -t girder/slicer_cli_web:small .``, or pulled from Docker Hub.

Batch Processing
----------------

All CLIs that take any single item, image, or files as inputs can be run on a set of such resources from a single directory.  For non-batch processing, the
ID of the image, item, or file is passed to ``<param>``.  For batch processing, the ID of a folder is passed to ``<param>_folder`` and a regular expression is passed to <param>.  All items in that folder whose name matches the regex are processed.  For images, only items that contain large_images are considered.  For files, the first file in each considered item is used.

If two inputs have batch specifications, there must be a one-to-one correspondence between the each of the lists of items determined by the folder ID and regular expression.  All of the lists are enumerated sorted by the lower case item name.

When running a batch job, a parent job initiates ordinary (non-batch) jobs.  The parent job will only start another child job when the most recent child job is no longer waiting to start.  This allows non-batch jobs or multiple batch jobs' children to naturally interleave.  The parent job can be canceled which will stop it from scheduling any more child jobs.

Templated Inputs
----------------

Any CLI parameter that takes a value that isn't a Girder resource identifer can be specified with a Jinja2-style template string.

For instance, instead of typing an explicit output file name, one can specify something like ``{{title}}-{{reference_base}}-{{now}}{{extension}}``.  If this were being run on a task called "Radial Blur" on an image called "SampleImage.tiff", where the output image referenced the image image and had a list of file extensions starting with ".png", this would end up being converted to the value ``Radial Blur-SampleImage-20210428-084321.png``.

The following template values are handled identically for all parameters:

- ``{{title}}``: the displayed CLI task title.
- ``{{task}}``: the internal task name (this usually doesn't have spaces in it)
- ``{{image}}``: the tag of the Docker image used for the task
- ``{{now}}``: the local time the job started in the form yyyymmdd-HHMMSS.  You can use ``yyyy``, ``mm``, ``dd``, ``HH``, ``MM``, ``SS`` for the four digit year, and two digit month, day, 24-hour, minute, and second.
- ``{{parameter_<name of cli parameter>}}``: any parameter that isn't templated can be referenced by its name.  For instance, in Example1 in the small-docker cli in this repo, ``{{parameter_stringChoice}}`` would get replaced by the value passed to the stringChoice parameter.
- ``{{parameter_<name of cli parameter>_base}}`` is the same as the previous item except that if the right-most part of the parameter looks like a file extension, it is removed.  This can be used to get the base name of file parameters.

There are also template values specific to individual parameters:

- ``{{name}}``: the name of this parameter.  This usually doesn't have any spaces in it.
- ``{{label}}``: the label of the is parameter.  This is what is displayed in the user interface.
- ``{{description}}``: the description of the parameter.
- ``{{index}}``: the index, if any, of the parameter.
- ``{{default}}``: the default value, if any, of the parameter.
- ``{{extension}}``: the first entry in the ``fileExtension`` value of the parameter, if any.
- ``{{reference}}``: if the parameter has a reference to another parameter, this returns that parameter's value.  It is equivalent to ``{{parameter_<reference>}}``.
- ``{{reference_base}}``: the reference value mentioned previously striped of the right-most file extension.


.. |build-status| image:: https://circleci.com/gh/girder/slicer_cli_web.svg?style=svg
    :target: https://circleci.com/gh/girder/slicer_cli_web
    :alt: Build Status

.. |codecov-io| image:: https://codecov.io/github/girder/slicer_cli_web/coverage.svg?branch=master
    :target: https://codecov.io/github/girder/slicer_cli_web?branch=master
    :alt: codecov.io

.. _Girder: http://girder.readthedocs.io/en/latest/
.. _Girder Worker: https://girder-worker.readthedocs.io/en/latest/
.. _HistomicsTK: https://github.com/DigitalSlideArchive/HistomicsTK

