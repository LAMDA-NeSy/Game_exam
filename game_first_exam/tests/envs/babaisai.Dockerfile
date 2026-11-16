FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib PYTHONUNBUFFERED=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
COPY game_first_exam/tests/envs/locks/babaisai.txt /requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --no-deps -r /requirements.txt
RUN pip check
WORKDIR /repo
