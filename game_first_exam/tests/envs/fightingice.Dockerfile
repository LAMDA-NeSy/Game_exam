FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates fontconfig libstdc++6 && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:51141204fe01a9f9dd74eab621d5eca7511eac67315c9975dbde5f2625bdca55 https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_linux_hotspot_21.0.2_13.tar.gz /tmp/java.tar.gz
RUN mkdir /opt/java && tar -xzf /tmp/java.tar.gz -C /opt/java --strip-components=1 && rm /tmp/java.tar.gz
ENV JAVA_HOME=/opt/java PATH=/opt/java/bin:$PATH FIGHTINGICE_HOME=/opt/fightingice PYTHONUNBUFFERED=1
COPY game_first_exam/tests/envs/locks/fightingice.txt /requirements.txt
RUN pip install --no-cache-dir --no-deps -r /requirements.txt && pip check
COPY game_first_exam/benchmarks/fightingice/install_native.py game_first_exam/benchmarks/fightingice/SOURCE.json /installer/
RUN python3 /installer/install_native.py /opt/fightingice
WORKDIR /repo
