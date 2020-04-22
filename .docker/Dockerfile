FROM python:3-slim

RUN groupadd -r uwsgi && \
    useradd -r -g uwsgi uwsgi && \
    mkdir -p /home/bot &&  \
    mkdir -p /home/config && \
    mkdir /root/.ssh && \
    chmod -R 700 /root/.ssh

ADD ./config/ /home/config/
ADD ./config/id_rsa /root/.ssh/
ADD ./config/cmd.sh /
RUN chown -R root:root /root/.ssh/
WORKDIR /home/bot

RUN apt-get update && \
    apt-get install -y gcc ssh && \
    pip install -r /home/config/requirements.txt && \
    pip install /home/config/gspread-3.3.0.tar.gz && \
    pip install /home/config/gsconfig-0.1.0.tar.gz

# CMD [ "uwsgi", "--ini", "/home/config/uwsgi.ini", "--http", "0.0.0.0:80" ]
CMD ["/cmd.sh"]
