FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1 PYGAME_HIDE_SUPPORT_PROMPT=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
COPY game_first_exam/benchmarks/chess/*requirements.txt /locks/
RUN pip install --require-hashes --retries 0 --timeout 30 -r /locks/build-requirements.txt \
    && pip install --require-hashes --no-build-isolation --retries 0 --timeout 30 -r /locks/requirements.txt \
    && pip check
WORKDIR /repo
