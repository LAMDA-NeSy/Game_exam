FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db AS clock-builder
ENV PYTHONUNBUFFERED=1 MPLBACKEND=Agg
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake flex bison libbz2-dev libncurses-dev zlib1g-dev git ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/mll-lab-nu/efe:minihack-files-0.1.5@sha256:62bae9e9facce6755dd0dbf38d2d7677fd6a8225fdc83c5e9bae7eac6c28e207 /install_clock.py /srv/install_clock.py
RUN python3 /srv/install_clock.py

FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
COPY --from=ghcr.io/mll-lab-nu/efe:minihack-files-0.1.5@sha256:62bae9e9facce6755dd0dbf38d2d7677fd6a8225fdc83c5e9bae7eac6c28e207 /requirements.txt /srv/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates libncurses6 libbz2-1.0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --no-deps setuptools==84.2.1 wheel==0.45.1
RUN pip install --no-cache-dir --no-deps --no-build-isolation -r /srv/requirements.txt && pip check
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:minihack-files-0.1.5@sha256:62bae9e9facce6755dd0dbf38d2d7677fd6a8225fdc83c5e9bae7eac6c28e207 /adapter.py /srv/adapter.py
COPY --from=ghcr.io/mll-lab-nu/efe:minihack-files-0.1.5@sha256:62bae9e9facce6755dd0dbf38d2d7677fd6a8225fdc83c5e9bae7eac6c28e207 /instance_schema.py /srv/instance_schema.py
COPY instance.json /srv/instance.json
COPY --from=clock-builder /usr/local/lib/minihack-clock.so /usr/local/lib/minihack-clock.so
COPY --from=clock-builder /usr/local/share/doc/minihack-clock /usr/local/share/doc/minihack-clock
ENV LD_PRELOAD=/usr/local/lib/minihack-clock.so FAKETIME="@2026-11-13 12:00:00" FAKETIME_DONT_FAKE_MONOTONIC=1 TZ=UTC
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
