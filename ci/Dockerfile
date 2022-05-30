FROM ubuntu:20.04

LABEL version="0.4"
LABEL description="KQCircuits image for CLI and CI"
LABEL org.opencontainers.image.source https://github.com/iqm-finland/KQCircuits

WORKDIR /kqc
ENV DISPLAY :99
ENV XDG_RUNTIME_DIR=/tmp
ARG DEBIAN_FRONTEND=noninteractive
ARG KL_FILE=klayout_0.27.9-1_amd64.deb

RUN apt-get update && apt-get install -y apt-utils && apt-get upgrade -y && \
    apt-get install -y wget xvfb python-is-python3 python3-pip git libcurl4 libglu1-mesa libxft-dev jq shellcheck graphviz && \
    wget -q https://www.klayout.org/downloads/Ubuntu-20/$KL_FILE && \
    echo "d0254078e04f49c7578bc9e577fe39cc  $KL_FILE" > klayout.md5 && \
    md5sum --check klayout.md5  && \
    apt-get install -y ./$KL_FILE && \
    apt-get clean -y && rm -rf /var/lib/apt/lists/* ./klayout* && apt-get clean && \
    python -m pip install --upgrade pip && \
    rm -rf /usr/lib/python3/dist-packages/klayout /usr/lib/python3/dist-packages/klayout.egg-info

# build from parent directory with -f ci/Dockerfile
COPY . /kqc
RUN ci/init_kqc.sh

ENTRYPOINT ["/bin/sh", "ci/run_script.sh"]
