FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
COPY test.sh instance.json /tests/
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /grade.py /tests/grade.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /tests/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /tests/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:pacman-files-0.1.0@sha256:6bec51b36730d5c42218d0cb7eccea95243a642665e780e50f4b33948a2984eb /instance_schema.py /tests/instance_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:pacman-files-0.1.0@sha256:6bec51b36730d5c42218d0cb7eccea95243a642665e780e50f4b33948a2984eb /metric_rules.py /tests/metric_rules.py
RUN chmod +x /tests/test.sh
# resources (PROTOCOL §6) # rcb-monitor
COPY --from=ghcr.io/mll-lab-nu/efe:monitor-0.5.0@sha256:ecc5f24f1516ca11711d7c2d3ac07c89f79cd9220812c1244498ec71e352402a /opt/rcb_monitor/rcb_limits.py /tests/rcb_limits.py
COPY rcb_limits.json /tests/rcb_limits.json
