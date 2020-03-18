FROM jupyter/r-notebook

RUN python -m pip install python-telegram-bot

USER root

ADD bot.py Listener.py callbacks.py config.py /home/jovyan/

WORKDIR /home/jovyan

USER $NB_UID
