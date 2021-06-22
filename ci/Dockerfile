FROM ubuntu:20.04

LABEL version="0.3"
LABEL description="This is a KQCircuit test environment including Klayout"
LABEL org.opencontainers.image.source https://github.com/iqm-finland/KQCircuits

WORKDIR /kqc
ENV DISPLAY :99
ENV XDG_RUNTIME_DIR=/tmp
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y apt-utils && apt-get upgrade -y && \
    apt-get install -y wget xvfb python-is-python3 python3-pip git libcurl4 && \
    wget -q https://www.klayout.org/downloads/Ubuntu-20/klayout_0.26.12-1_amd64.deb && \
    echo "d075f942955294e96702caec5705125f  klayout_0.26.12-1_amd64.deb" > klayout.md5 && \
    md5sum --check klayout.md5  && \
    apt-get install -y ./klayout_0.26.12-1_amd64.deb && \
    apt-get clean -y && rm -rf /var/lib/apt/lists/* ./klayout* && apt-get clean && \
    python -m pip install --upgrade pip
