FROM python:3.11-slim
MAINTAINER David Manthey <david.manthey@kitware.com>

RUN pip install --no-cache--dir --find-links https://girder.github.io/large_image_wheels large_image[sources]
RUN pip install --no-cache--dir girder-slicer-cli-web
RUN pip install --no-cache--dir girder-client

COPY . $PWD
ENTRYPOINT ["python", "./cli_list.py"]
