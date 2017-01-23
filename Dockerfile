FROM ubuntu:16.04

RUN apt-get update && apt-get -y dist-upgrade \
    && apt-get -y install python-pip uwsgi virtualenv sudo python-dev libyaml-dev \
       libsasl2-dev libldap2-dev nginx uwsgi-plugin-python \
    && rm -rf /var/cache/apt/archives/*

RUN useradd -m -s /bin/bash iris

ADD docker/daemons /home/iris/daemons
ADD setup.py /home/iris/setup.py
ADD src /home/iris/src

RUN chown -R iris:iris /home/iris /var/log/nginx /var/lib/nginx \
    && sudo -Hu iris mkdir -p /home/iris/var/log/uwsgi /home/iris/var/log/nginx /home/iris/var/run \
    && sudo -Hu iris virtualenv /home/iris/env \
    && sudo -Hu iris /bin/bash -c 'source /home/iris/env/bin/activate && python /home/iris/setup.py install'

EXPOSE 16650

# uwsgi runs nginx. see uwsgi.yaml for details
CMD ["/usr/bin/uwsgi", "--yaml", "/home/iris/daemons/uwsgi.yaml:prod"]
