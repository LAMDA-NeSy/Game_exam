FROM docker.io/library/python:3.10.12-slim-bookworm@sha256:4d440b214e447deddc0a94de23a3d97d28dfafdf125a8b4bb8073381510c9ee2
ENV PYTHONUNBUFFERED=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYGAME_HIDE_SUPPORT_PROMPT=1 VMAGE_ROOT=/opt/vmage
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libgl1 libglib2.0-0 fonts-dejavu-core=2.37-6 && rm -rf /var/lib/apt/lists/*
COPY game_first_exam/tests/envs/locks/vmage.txt /requirements.txt
RUN pip install --no-cache-dir --no-deps -r /requirements.txt
RUN pip check
COPY game_first_exam/benchmarks/vmage/common/source_loader.py game_first_exam/benchmarks/vmage/common/SOURCE.json /opt/vmage-installer/
RUN python /opt/vmage-installer/source_loader.py --destination /opt/vmage
# Bound BLAS threads to the simulator PID/CPU quota; native game logic is unchanged.
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /repo
