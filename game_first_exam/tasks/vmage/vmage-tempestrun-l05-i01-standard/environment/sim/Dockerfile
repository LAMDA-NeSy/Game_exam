FROM docker.io/library/python:3.10.12-slim-bookworm@sha256:4d440b214e447deddc0a94de23a3d97d28dfafdf125a8b4bb8073381510c9ee2
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYGAME_HIDE_SUPPORT_PROMPT=1 VMAGE_ROOT=/opt/vmage
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libgl1 libglib2.0-0 fonts-dejavu-core=2.37-6 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/mll-lab-nu/efe:vmage-files-0.2.1@sha256:e7e84a16ce785ff78ca7ef18f915ff5d0927b5c76937c66c485082d7024eb3ee /common/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir --no-deps -r /srv/requirements.txt && pip check
COPY --from=ghcr.io/mll-lab-nu/efe:vmage-files-0.2.1@sha256:e7e84a16ce785ff78ca7ef18f915ff5d0927b5c76937c66c485082d7024eb3ee /common/source_loader.py /srv/source_loader.py
COPY --from=ghcr.io/mll-lab-nu/efe:vmage-files-0.2.1@sha256:e7e84a16ce785ff78ca7ef18f915ff5d0927b5c76937c66c485082d7024eb3ee /common/SOURCE.json /srv/SOURCE.json
COPY --from=ghcr.io/mll-lab-nu/efe:vmage-files-0.2.1@sha256:e7e84a16ce785ff78ca7ef18f915ff5d0927b5c76937c66c485082d7024eb3ee /common/vmage_bridge.py /srv/vmage_bridge.py
RUN python3 /srv/source_loader.py --destination /opt/vmage
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:vmage-files-0.2.1@sha256:e7e84a16ce785ff78ca7ef18f915ff5d0927b5c76937c66c485082d7024eb3ee /tempestrun/adapter.py /srv/adapter.py
COPY --from=ghcr.io/mll-lab-nu/efe:vmage-files-0.2.1@sha256:e7e84a16ce785ff78ca7ef18f915ff5d0927b5c76937c66c485082d7024eb3ee /tempestrun/instance_schema.py /srv/instance_schema.py
COPY instance.json /srv/instance.json
# Bound BLAS threads to the simulator PID/CPU quota; native game logic is unchanged.
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
