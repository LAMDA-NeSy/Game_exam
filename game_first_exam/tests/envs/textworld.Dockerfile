FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libffi-dev curl git wget && rm -rf /var/lib/apt/lists/*
COPY game_first_exam/tests/envs/locks/textworld.txt /requirements.txt
RUN pip install --no-cache-dir --no-deps -r /requirements.txt
RUN pip install --no-cache-dir --no-deps --only-binary=:all: --platform manylinux2014_x86_64 --target /opt/textworld textworld==1.7.0
ENV PYTHONPATH=/opt/textworld
COPY game_first_exam/tests/envs/check_textworld.py /check_textworld.py
RUN PYTHONPATH= pip check && python /check_textworld.py
WORKDIR /repo
