FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db AS client
WORKDIR /app
COPY fle_client.py /opt/fle_client.py

FROM client AS recorder
COPY adapter.py /opt/adapter.py
RUN mkdir -p /channel /evidence && chown 65534:65534 /channel /evidence
USER 65534:65534
CMD ["python", "/opt/adapter.py"]

FROM client AS main
RUN mkdir -p /channel && chown 65534:65534 /channel
