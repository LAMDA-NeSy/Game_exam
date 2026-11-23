FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
COPY --from=ghcr.io/mll-lab-nu/efe:slimevolley-files-1.0.0@sha256:bb15a9bd6fefc604d6961778781bb04e19abcfa6913e289ff743af7ccaab54d5 /requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir setuptools==84.2.1 wheel==0.45.1 \
    && pip install --no-cache-dir --no-build-isolation --no-deps -r /srv/requirements.txt
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:slimevolley-files-1.0.0@sha256:bb15a9bd6fefc604d6961778781bb04e19abcfa6913e289ff743af7ccaab54d5 /adapter.py /srv/adapter.py
COPY --from=ghcr.io/mll-lab-nu/efe:slimevolley-files-1.0.0@sha256:bb15a9bd6fefc604d6961778781bb04e19abcfa6913e289ff743af7ccaab54d5 /instance_schema.py /srv/instance_schema.py
COPY instance.json /srv/instance.json
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
