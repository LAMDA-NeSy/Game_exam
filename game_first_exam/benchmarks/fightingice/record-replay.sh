#!/usr/bin/env bash
set -euo pipefail

cd /tmp
for asset in FightingICE.jar lib data; do
    ln -s "/install/$asset" "$asset"
done
mkdir -p log/replay /tmp/cache
ln -s /input/match.dat log/replay/match.dat
export XDG_CACHE_HOME=/tmp/cache SERVER_HOST=127.0.0.1

java -cp 'FightingICE.jar:lib/*:lib/grpc/*:lib/lwjgl/*:lib/lwjgl/natives/linux/amd64/*' \
    Main --c1 "$1" --c2 "$1" --limithp 400 400 --mute > /out/engine.log 2>&1 &
game=$!
capture=
trap 'if [[ -n "$capture" ]]; then kill -INT "$capture" 2>/dev/null || true; wait "$capture" || true; fi; kill "$game" 2>/dev/null || true; wait "$game" || true' EXIT

window=$(timeout 25 xdotool search --sync --onlyvisible --name '^DareFightingICE$')
xdotool windowfocus --sync "$window"
until grep -q 'Socket server is started' /out/engine.log; do
    kill -0 "$game"
    sleep .1
done
# The first display update installs the home menu's key handlers.
sleep .5
xdotool key --delay 250 Down z

ffmpeg -nostdin -loglevel warning -f x11grab -framerate 30 -video_size 960x640 \
    -draw_mouse 0 -i "$DISPLAY" -an -c:v libx264 -threads 2 -preset veryfast \
    -crf 21 -pix_fmt yuv420p -movflags +faststart /out/capture.mp4 > /out/ffmpeg.log 2>&1 &
capture=$!
while [[ $(grep -c 'Round Duration:' /out/engine.log || true) -lt 3 ]]; do
    kill -0 "$game" "$capture"
    sleep .2
done
kill -INT "$capture"
wait "$capture" || [[ $? == 255 ]]
capture=
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height \
    -show_entries format=duration -of json /out/capture.mp4 > /out/video.json
ffmpeg -nostdin -v error -ss 5 -i /out/capture.mp4 -frames:v 1 -update 1 /out/poster.jpg
