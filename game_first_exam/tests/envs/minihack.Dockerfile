FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db AS clock-builder
ENV PYTHONUNBUFFERED=1 MPLBACKEND=Agg
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake flex bison libbz2-dev libncurses-dev zlib1g-dev git ca-certificates && rm -rf /var/lib/apt/lists/*
COPY game_first_exam/benchmarks/minihack/install_clock.py /srv/install_clock.py
RUN python3 /srv/install_clock.py

FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1
COPY game_first_exam/tests/envs/locks/minihack.txt /srv/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates libncurses6 libbz2-1.0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --no-deps setuptools==84.2.1 wheel==0.45.1
RUN pip install --no-cache-dir --no-deps --no-build-isolation -r /srv/requirements.txt && pip check
COPY --from=clock-builder /usr/local/lib/minihack-clock.so /usr/local/lib/minihack-clock.so
COPY --from=clock-builder /usr/local/share/doc/minihack-clock /usr/local/share/doc/minihack-clock
ENV LD_PRELOAD=/usr/local/lib/minihack-clock.so FAKETIME="@2026-11-13 12:00:00" FAKETIME_DONT_FAKE_MONOTONIC=1 TZ=UTC
WORKDIR /repo
