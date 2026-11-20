FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
COPY --from=ghcr.io/mll-lab-nu/efe:vizdoom-files-1.2.1@sha256:d1b51e9104a736458752e9bd32fe760da8fe07bc865d7d0be9b8e98392dc96b3 /requirements.txt /srv/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libsdl2-2.0-0 libgl1 libglib2.0-0 ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r /srv/requirements.txt && pip check
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:vizdoom-files-1.2.1@sha256:d1b51e9104a736458752e9bd32fe760da8fe07bc865d7d0be9b8e98392dc96b3 /adapter.py /srv/adapter.py
COPY --from=ghcr.io/mll-lab-nu/efe:vizdoom-files-1.2.1@sha256:d1b51e9104a736458752e9bd32fe760da8fe07bc865d7d0be9b8e98392dc96b3 /instance_schema.py /srv/instance_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:vizdoom-files-1.2.1@sha256:d1b51e9104a736458752e9bd32fe760da8fe07bc865d7d0be9b8e98392dc96b3 /vizdoom_actions.py /srv/vizdoom_actions.py
COPY --from=ghcr.io/mll-lab-nu/efe:vizdoom-files-1.2.1@sha256:d1b51e9104a736458752e9bd32fe760da8fe07bc865d7d0be9b8e98392dc96b3 /vizdoom_server.py /srv/vizdoom_server.py
COPY instance.json /srv/instance.json
WORKDIR /srv
CMD ["python3", "/srv/vizdoom_server.py"]
