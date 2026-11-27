FROM game-exam:fightingice-competition
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb xauth xdotool ffmpeg libgl1 libgl1-mesa-dri libxrandr2 libxi6 \
    && rm -rf /var/lib/apt/lists/*
ENV LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=2 JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=2
COPY record-replay.sh /record-replay.sh
ENTRYPOINT ["timeout", "--kill-after=5", "250", "xvfb-run", "-a", "-s", "-screen 0 960x640x24 -nolisten tcp", "bash", "/record-replay.sh"]
