FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1 PYGAME_HIDE_SUPPORT_PROMPT=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
COPY --from=ghcr.io/mll-lab-nu/efe:chess-files-0.1.2@sha256:75f183dd662d4388d072ea4f5d266fecace649176074d226f14e13caee106add /build-requirements.txt /chess-requirements.txt /requirements.txt /locks/
RUN pip install --require-hashes --retries 0 --timeout 30 -r /locks/build-requirements.txt \
    && pip install --require-hashes --no-build-isolation --retries 0 --timeout 30 -r /locks/requirements.txt \
    && pip check
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /reducers.py /config_schema.py /contracts.py /encoding.py /recording.py /srv/
COPY --from=ghcr.io/mll-lab-nu/efe:chess-files-0.1.2@sha256:75f183dd662d4388d072ea4f5d266fecace649176074d226f14e13caee106add /adapter.py /instance_schema.py /metric_rules.py /opponent.py /srv/
COPY instance.json /srv/instance.json
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
