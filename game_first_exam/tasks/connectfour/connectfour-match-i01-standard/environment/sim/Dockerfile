FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
ENV PYTHONUNBUFFERED=1 PYGAME_HIDE_SUPPORT_PROMPT=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
COPY --from=ghcr.io/mll-lab-nu/efe:connectfour-files-0.1.0@sha256:6c81b2a06c9246b4471a343f9657a4d48485fa02c827672cfbefd43cd473b850 /requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /server.py /srv/server.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /reducers.py /srv/reducers.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /config_schema.py /srv/config_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /contracts.py /srv/contracts.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /encoding.py /srv/encoding.py
COPY --from=ghcr.io/mll-lab-nu/efe:game-files-0.6.0@sha256:bfb708928954d5cc194a614ab772a65b1e56f381b49dfeb2227c3d609e5f2ecc /recording.py /srv/recording.py
COPY --from=ghcr.io/mll-lab-nu/efe:connectfour-files-0.1.0@sha256:6c81b2a06c9246b4471a343f9657a4d48485fa02c827672cfbefd43cd473b850 /adapter.py /srv/adapter.py
COPY --from=ghcr.io/mll-lab-nu/efe:connectfour-files-0.1.0@sha256:6c81b2a06c9246b4471a343f9657a4d48485fa02c827672cfbefd43cd473b850 /instance_schema.py /srv/instance_schema.py
COPY --from=ghcr.io/mll-lab-nu/efe:connectfour-files-0.1.0@sha256:6c81b2a06c9246b4471a343f9657a4d48485fa02c827672cfbefd43cd473b850 /opponent.py /srv/opponent.py
COPY instance.json /srv/instance.json
WORKDIR /srv
CMD ["python3", "/srv/server.py"]
