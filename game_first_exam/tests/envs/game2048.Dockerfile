FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 ca-certificates fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY game_first_exam/tests/envs/locks/game2048.txt /requirements.txt
RUN pip install --no-cache-dir --no-deps -r /requirements.txt
RUN pip check
WORKDIR /repo
