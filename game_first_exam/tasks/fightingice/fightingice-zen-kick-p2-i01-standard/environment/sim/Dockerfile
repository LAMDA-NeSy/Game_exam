FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates fontconfig libstdc++6 && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:51141204fe01a9f9dd74eab621d5eca7511eac67315c9975dbde5f2625bdca55 https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_linux_hotspot_21.0.2_13.tar.gz /tmp/java.tar.gz
RUN mkdir /opt/java && tar -xzf /tmp/java.tar.gz -C /opt/java --strip-components=1 && rm /tmp/java.tar.gz
ENV JAVA_HOME=/opt/java PATH=/opt/java/bin:$PATH FIGHTINGICE_HOME=/opt/fightingice PYTHONUNBUFFERED=1 SERVER_HOST=127.0.0.1
COPY --from=ghcr.io/mll-lab-nu/efe:fightingice-files-0.1.0@sha256:20832c27e23b258cb2a489c6614e531e35b535d83c662bb5e99ab2db47830e71 /requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir --no-deps -r /srv/requirements.txt && pip check
COPY --from=ghcr.io/mll-lab-nu/efe:fightingice-files-0.1.0@sha256:20832c27e23b258cb2a489c6614e531e35b535d83c662bb5e99ab2db47830e71 /install_native.py /SOURCE.json /LICENSE-pyftg /srv/
RUN python3 /srv/install_native.py /opt/fightingice
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /contracts.py /config_schema.py /reducers.py /encoding.py /recording.py /srv/
COPY --from=ghcr.io/mll-lab-nu/efe:fightingice-files-0.1.0@sha256:20832c27e23b258cb2a489c6614e531e35b535d83c662bb5e99ab2db47830e71 /adapter.py /bridge.py /instance_schema.py /srv/
COPY instance.json /srv/instance.json
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
