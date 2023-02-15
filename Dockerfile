FROM jupyter/scipy-notebook

RUN python -m pip install python-telegram-bot pyyaml octave_kernel

USER root

RUN apt-get -y update \
 && apt-get -y install \
    libcurl4-openssl-dev \
    gnuplot octave liboctave-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# R pre-requisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-dejavu \
    unixodbc \
    unixodbc-dev \
    r-cran-rodbc \
    gfortran \
    gcc && \
    rm -rf /var/lib/apt/lists/*

ADD bot2.py Listener.py callbacks.py config.py /home/jovyan/

WORKDIR /home/jovyan/work

USER $NB_UID
