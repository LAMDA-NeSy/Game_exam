FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1 MPLBACKEND=Agg
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Native poke-env fork (VGC doubles support) and pinned runtime deps.
COPY --from=ghcr.io/mll-lab-nu/efe:vgc-files-0.1.0@sha256:dc627df46c11cc6bbc5d513b351cdc07be2d5f27ff4081195133901b827b066c /requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt

# Pin the native Pokemon Showdown simulator to the vgc-bench submodule commit.
# TODO(isolation): ensure Showdown binds 127.0.0.1 only so the agent container cannot
# reach it over the compose network; the exact bind mechanism (config.js `host` or a
# CLI flag) must be confirmed against this pinned commit.
RUN git clone --depth 1 https://github.com/smogon/pokemon-showdown.git /srv/pokemon-showdown \
    && cd /srv/pokemon-showdown \
    && git fetch --depth 1 origin 913da3602a3aa1db79f9fdc5d5222eaf8d39569d \
    && git checkout 913da3602a3aa1db79f9fdc5d5222eaf8d39569d \
    && npm install --no-audit --no-fund

# Trusted game service and shared runtime files.
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:vgc-files-0.1.0@sha256:dc627df46c11cc6bbc5d513b351cdc07be2d5f27ff4081195133901b827b066c /adapter.py /srv/adapter.py
COPY --from=ghcr.io/mll-lab-nu/efe:vgc-files-0.1.0@sha256:dc627df46c11cc6bbc5d513b351cdc07be2d5f27ff4081195133901b827b066c /instance_schema.py /srv/instance_schema.py
COPY instance.json /srv/instance.json
WORKDIR /srv
# Start the native Showdown server on loopback, wait for it, then run the trusted
# game service (HTTP) that the agent reaches through the compose network.
CMD ["bash", "-c", "cd /srv/pokemon-showdown && node pokemon-showdown start 7200 --no-security & sleep 6; exec python3 /srv/server.py"]
