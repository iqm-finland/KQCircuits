FROM ubuntu:20.04

LABEL version="0.1"
LABEL description="This is a KQCircuit test environment including Klayout"

WORKDIR /kqc
ENV DISPLAY :99
ENV XDG_RUNTIME_DIR=/tmp
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y apt-utils wget xvfb python-is-python3 python3-pip git && \
    wget -q https://www.klayout.org/downloads/Ubuntu-20/klayout_0.26.9-1_amd64.deb && \
    echo "8287ce4148dc36aefaac61bedc74e60b  klayout_0.26.9-1_amd64.deb" > klayout.md5 && \
    md5sum --check klayout.md5  && \
    apt-get install -y ./klayout_0.26.9-1_amd64.deb && \
    apt-get clean -y && rm -rf /var/lib/apt/lists/* ./klayout* && apt-get clean && \
    ln -s /usr/bin/pip3 /usr/bin/pip && \
    python -m pip install --upgrade pip

RUN mkdir -p /root/.klayout/python && cd /root/.klayout/python && \
    ln -s /builds/iqm/qe/KQCircuits/kqcircuits kqcircuits && ln -s /builds/iqm/qe/KQCircuits/scripts kqcircuits_scripts
