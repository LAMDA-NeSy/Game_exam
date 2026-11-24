FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1
COPY --from=ghcr.io/mll-lab-nu/efe:pacman-files-0.1.0@sha256:6bec51b36730d5c42218d0cb7eccea95243a642665e780e50f4b33948a2984eb /requirements.txt /srv/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r /srv/requirements.txt
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:pacman-files-0.1.0@sha256:6bec51b36730d5c42218d0cb7eccea95243a642665e780e50f4b33948a2984eb /adapter.py /srv/adapter.py
RUN python -m playwright install --with-deps --only-shell chromium
RUN git init /tmp/upstream && cd /tmp/upstream && git remote add origin https://github.com/gameworld-project/GameWorld-Games.git && git sparse-checkout init --cone && git sparse-checkout set benchmark/30_pacman && git fetch --depth=1 --filter=blob:none origin e5ddb16df85b91a1d17bb0577621cc7c5e65d738 && git checkout --detach FETCH_HEAD && mv benchmark/30_pacman /srv/game && rm -rf /tmp/upstream
COPY --from=ghcr.io/mll-lab-nu/efe:pacman-files-0.1.0@sha256:6bec51b36730d5c42218d0cb7eccea95243a642665e780e50f4b33948a2984eb /instance_schema.py /srv/instance_schema.py
COPY instance.json /srv/instance.json
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
