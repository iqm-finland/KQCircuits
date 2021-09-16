FROM ubuntu:20.04

LABEL version="0.4"
LABEL description="KQCircuits image for CLI and CI"
LABEL org.opencontainers.image.source https://github.com/iqm-finland/KQCircuits

WORKDIR /kqc
ENV DISPLAY :99
ENV XDG_RUNTIME_DIR=/tmp
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y apt-utils && apt-get upgrade -y && \
    apt-get install -y wget xvfb python-is-python3 python3-pip git libcurl4 && \
    wget -q https://www.klayout.org/downloads/Ubuntu-20/klayout_0.27.3-1_amd64.deb && \
    echo "5779feaecc03d85e31b174088b6232c7  klayout_0.27.3-1_amd64.deb" > klayout.md5 && \
    md5sum --check klayout.md5  && \
    apt-get install -y ./klayout_0.27.3-1_amd64.deb && \
    apt-get clean -y && rm -rf /var/lib/apt/lists/* ./klayout* && apt-get clean && \
    python -m pip install --upgrade pip

# build from parent directory with -f ci/Dockerfile
COPY . /kqc
RUN ci/init_kqc.sh

ENTRYPOINT ["/bin/sh", "ci/run_script.sh"]