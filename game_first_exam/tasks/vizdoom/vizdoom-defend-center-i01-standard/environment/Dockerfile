FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
RUN apt-get update && apt-get install -y --no-install-recommends bash curl git nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @openai/codex@0.167.1 && npm cache clean --force
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /game_client.py /app/standard_game_client.py
COPY --from=ghcr.io/mll-lab-nu/efe:vizdoom-files-1.2.1@sha256:d1b51e9104a736458752e9bd32fe760da8fe07bc865d7d0be9b8e98392dc96b3 /vizdoom_client.py /app/game_client.py
COPY --from=ghcr.io/mll-lab-nu/efe:vizdoom-files-1.2.1@sha256:d1b51e9104a736458752e9bd32fe760da8fe07bc865d7d0be9b8e98392dc96b3 /vizdoom_actions.py /app/vizdoom_actions.py
COPY --from=ghcr.io/mll-lab-nu/efe:connection-files-0.1.0@sha256:6d1002dea6ca507b4148d3196e233838e645b33bcfa9a27ae4a43027ae519999 /service_connection.py /app/service_connection.py
RUN printf '%s\n' 'pillow==10.4.0 --hash=sha256:86dcb5a1eb778d8b25659d5e4341269e8590ad6b4e8b44d9f4b07f8d136c414a' > /tmp/image-tools.txt \
    && pip install --no-cache-dir --only-binary=:all: --require-hashes -r /tmp/image-tools.txt \
    && rm /tmp/image-tools.txt
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app
RUN mkdir -p /app/output
WORKDIR /app
