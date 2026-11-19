FROM docker.io/library/python:3.10.18-slim-bookworm@sha256:445b9efb2c047a7ccdb30d293fd6b1aa0f62a55062dc2b69051df91e10848749
ENV PYTHONUNBUFFERED=1
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources && apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libatomic1 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY game_first_exam/tests/envs/locks/coinrun.txt /srv/requirements.txt
RUN pip install --no-cache-dir --no-deps setuptools==80.9.0 wheel==0.45.1
RUN pip install --no-cache-dir --no-deps --no-build-isolation -r /srv/requirements.txt && pip check
WORKDIR /repo
