FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
RUN apt-get update && apt-get install -y --no-install-recommends bash curl git nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @openai/codex@0.167.1 && npm cache clean --force
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir numpy==1.26.4 Pillow==10.4.0
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /game_client.py /app/game_client.py
COPY --from=ghcr.io/mll-lab-nu/efe:connection-files-0.1.0@sha256:6d1002dea6ca507b4148d3196e233838e645b33bcfa9a27ae4a43027ae519999 /service_connection.py /app/service_connection.py
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app
RUN mkdir -p /app/output
WORKDIR /app

COPY --from=ghcr.io/mll-lab-nu/efe:game-modes-files-0.2.0@sha256:f04281f547b3889635e456088ab2ef9d7821bdece0acac9cae3762965e66e615 /realtime_client.py /app/realtime_client.py
