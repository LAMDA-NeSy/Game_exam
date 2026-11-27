FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates fontconfig libstdc++6 libasound2 && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:51141204fe01a9f9dd74eab621d5eca7511eac67315c9975dbde5f2625bdca55 https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_linux_hotspot_21.0.2_13.tar.gz /tmp/java.tar.gz
RUN mkdir /opt/java && tar -xzf /tmp/java.tar.gz -C /opt/java --strip-components=1 && rm /tmp/java.tar.gz
COPY requirements.txt /bridge/requirements.txt
RUN pip install --no-cache-dir --no-deps -r /bridge/requirements.txt && pip check
COPY competition_results.py competition_wire.py competition_match.py /bridge/
ENV JAVA_HOME=/opt/java PATH=/opt/java/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 ALSOFT_DRIVERS=null
