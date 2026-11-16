FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
COPY --from=ghcr.io/mll-lab-nu/efe:textworld-files-0.4.1@sha256:15e74c5427de7afcf88864f64b29c19acf11f16e007afa6905422518058679c1 /requirements.txt /srv/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libffi-dev curl git wget && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --no-deps -r /srv/requirements.txt
RUN pip install --no-cache-dir --no-deps --only-binary=:all: --platform manylinux2014_x86_64 --target /opt/textworld textworld==1.7.0
ENV PYTHONPATH=/opt/textworld
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:textworld-files-0.4.1@sha256:15e74c5427de7afcf88864f64b29c19acf11f16e007afa6905422518058679c1 /adapter.py /srv/adapter.py
COPY --from=ghcr.io/mll-lab-nu/efe:textworld-files-0.4.1@sha256:15e74c5427de7afcf88864f64b29c19acf11f16e007afa6905422518058679c1 /instance_schema.py /srv/instance_schema.py
COPY instance.json /srv/instance.json
COPY game.z8 game.json /srv/
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
