Iris-frontend under Docker
=========================

### Get started

Build container. This installs all dependencies as well as copies all iris-frontend source code.

    docker build -t iris-frontend .

Edit iris-frontend's config file to reflect where you have iris-api running:

    vim docker/config/config.yaml

Run it, with bind mounts to give access to iris frontend config file:

    docker run -p 16650:16650 -v `pwd`/docker/config:/home/iris/config -t iris-frontend

You can optionally bind mount log directories for uwsgi/nginx:

    mkdir -p docker/logs
    docker run -p 16650:16650 -v `pwd`/docker/config:/home/iris/config \
    -v `pwd`/docker/logs/nginx:/home/iris/var/log/nginx  \
    -v `pwd`/docker/logs/uwsgi:/home/iris/var/log/uwsgi  -t iris-frontend

You can then hit `http://localhost:16650 ` to access iris-frontend running within the docker.

### Quick commands

Check what containers are running:

    docker ps

Kill and remove a container:

    docker rm -f $ID

Execute a bash shell inside container while it's running:

    docker exec -i -t $ID /bin/bash