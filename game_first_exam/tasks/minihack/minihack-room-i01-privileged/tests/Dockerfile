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
COPY instance.json mode.json test.sh rcb_limits.json /tests/
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /grade.py /tests/grade.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /tests/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /tests/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:minihack-files-0.1.5@sha256:62bae9e9facce6755dd0dbf38d2d7677fd6a8225fdc83c5e9bae7eac6c28e207 /metric_rules.py /tests/metric_rules.py
COPY --from=ghcr.io/mll-lab-nu/efe:minihack-files-0.1.5@sha256:62bae9e9facce6755dd0dbf38d2d7677fd6a8225fdc83c5e9bae7eac6c28e207 /instance_schema.py /tests/instance_schema.py
ENV PYTHONPATH=/tests:/srv
RUN chmod +x /tests/test.sh
WORKDIR /tests
COPY --from=ghcr.io/mll-lab-nu/efe:game-modes-files-0.2.0@sha256:f04281f547b3889635e456088ab2ef9d7821bdece0acac9cae3762965e66e615 /mode_grade.py /tests/mode_grade.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-modes-files-0.2.0@sha256:f04281f547b3889635e456088ab2ef9d7821bdece0acac9cae3762965e66e615 /mode_config.py /tests/mode_config.py
# resources (PROTOCOL §6) # rcb-monitor
COPY --from=ghcr.io/mll-lab-nu/efe:monitor-0.5.0@sha256:ecc5f24f1516ca11711d7c2d3ac07c89f79cd9220812c1244498ec71e352402a /opt/rcb_monitor/rcb_limits.py /tests/rcb_limits.py
COPY rcb_limits.json /tests/rcb_limits.json
