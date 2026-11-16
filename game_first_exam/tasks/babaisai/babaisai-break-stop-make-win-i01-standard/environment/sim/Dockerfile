FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib PYTHONUNBUFFERED=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
COPY --from=ghcr.io/mll-lab-nu/efe:babaisai-files-0.3.0@sha256:15bc33bb6f4d90c4a09185c8ef96a170c6ee7fcee9ccc8635196926c14bc95ac /requirements.txt /srv/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --no-deps -r /srv/requirements.txt
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:babaisai-files-0.3.0@sha256:15bc33bb6f4d90c4a09185c8ef96a170c6ee7fcee9ccc8635196926c14bc95ac /adapter.py /srv/adapter.py
COPY --from=ghcr.io/mll-lab-nu/efe:babaisai-files-0.3.0@sha256:15bc33bb6f4d90c4a09185c8ef96a170c6ee7fcee9ccc8635196926c14bc95ac /vendor/ /srv/vendor/
COPY --from=ghcr.io/mll-lab-nu/efe:babaisai-files-0.3.0@sha256:15bc33bb6f4d90c4a09185c8ef96a170c6ee7fcee9ccc8635196926c14bc95ac /instance_schema.py /srv/instance_schema.py
COPY instance.json /srv/instance.json
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
