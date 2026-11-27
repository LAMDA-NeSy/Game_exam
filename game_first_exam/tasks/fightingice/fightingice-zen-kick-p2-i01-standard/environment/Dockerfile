FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
RUN python3 -c "from pathlib import Path; p = Path('/etc/apt/sources.list.d/debian.sources'); p.write_text(p.read_text().replace('http://deb.debian.org', 'https://deb.debian.org'))" \
    && apt-get -o Acquire::Retries=3 -o Acquire::https::Timeout=30 update \
    && apt-get -o Acquire::Retries=3 -o Acquire::https::Timeout=30 install -y --no-install-recommends bash curl git nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @openai/codex@0.167.1 && npm cache clean --force
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /game_client.py /app/game_client.py
COPY --from=ghcr.io/mll-lab-nu/efe:connection-files-0.1.0@sha256:6d1002dea6ca507b4148d3196e233838e645b33bcfa9a27ae4a43027ae519999 /service_connection.py /app/service_connection.py
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app
RUN mkdir -p /app/output
WORKDIR /app
