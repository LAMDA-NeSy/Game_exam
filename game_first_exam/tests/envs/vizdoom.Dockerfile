FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
RUN apt-get update && apt-get install -y --no-install-recommends libsdl2-2.0-0 libgl1 libglib2.0-0 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY game_first_exam/benchmarks/vizdoom/requirements.txt /requirements.txt
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r /requirements.txt && pip check
WORKDIR /repo
