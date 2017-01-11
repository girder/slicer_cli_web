# Use a version of alpine that includes bash and python
FROM jfloff/alpine-python:2.7
MAINTAINER David Manthey <david.manthey@kitware.com>

# Since we are using a BusyBox varient, we need to use addgroup and adduser,
# rather than let girder_worker use groupadd and useradd.  Those will fail,
# which is allowed if the worker user and group exist.
RUN addgroup -g 1000 -S worker
RUN adduser -u 1000 -h /home/worker -S -G worker -s /bin/bash worker

# Suppress errors from groupadd and useradd
RUN touch /usr/local/bin/groupadd
RUN chmod a+x /usr/local/bin/groupadd
RUN touch /usr/local/bin/useradd
RUN chmod a+x /usr/local/bin/useradd

# We need ctk-cli to parse inputs
RUN pip install ctk-cli
COPY . $PWD

ENTRYPOINT ["python", "./cli_list.py"]