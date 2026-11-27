"""Trusted runner for one native match. Never imports a submitted controller."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from contextlib import ExitStack

from competition_results import TRACKS, read_match
from competition_wire import packet, public_state, receive, send


PORT = 31415


def relay(native, player, *, audio=True):
    from google.protobuf.message import DecodeError
    from pyftg.models.enums.flag import Flag
    from pyftg.protoc.message_pb2 import GrpcKey
    from pyftg.protoc.service_pb2 import PlayerGameState

    callbacks = 0
    round_results = []
    while True:
        tag = receive(native, 1)
        if tag == b"\0":
            if player is not None:
                try:
                    player.sendall(tag)
                except OSError:
                    player = None
            return {"callbacks": callbacks, "controller_disconnected": player is None,
                    "round_results": round_results}
        if tag != b"\1":
            raise ValueError("unexpected native player message")
        flag, state = public_state(PlayerGameState.FromString(packet(native)), audio=audio)
        if flag == Flag.INITIALIZE:
            round_results = []
        if flag in (Flag.ROUND_END, Flag.GAME_END):
            result = state.round_result
            round_results.append([result.current_round, *result.remaining_hps, result.elapsed_frame])
        key = GrpcKey()
        if player is not None:
            try:
                player.sendall(tag)
                send(player, state.SerializeToString())
                if flag == Flag.PROCESSING:
                    key.ParseFromString(packet(player, 128))
                    key.DiscardUnknownFields()
            except (OSError, EOFError, ValueError, DecodeError):
                # The engine clock keeps running. Seal this failure independently of the native outcome.
                player = None
        if flag == Flag.PROCESSING:
            callbacks += 1
            send(native, key.SerializeToString())


def play(root, evidence, match, bridges, *, audio):
    from pyftg.protoc.service_pb2 import InitializeRequest, RunGameRequest, RunGameResponse

    character, baseline, _ = TRACKS[match["track"]]
    names = [match["p1"], match["p2"]]
    for side, name in enumerate(names, 1):
        if side not in bridges and name != baseline:
            raise ValueError("only the track's native MCTS baseline may run inside the engine")
    with ExitStack() as stack:
        listeners = {}
        for side, path in bridges.items():
            listener = stack.enter_context(socket.socket(socket.AF_UNIX))
            listener.bind(path)
            os.chmod(path, 0o666)
            listener.listen(1)
            listener.settimeout(60)
            listeners[side] = listener
        players = {side: stack.enter_context(listener.accept()[0]) for side, listener in listeners.items()}
        for player in players.values():
            player.settimeout(1)
        log = stack.enter_context((evidence / "engine.log").open("wb"))
        proc = subprocess.Popen(
            ["java", "-cp", "FightingICE.jar:lib/*:lib/lwjgl/*:lib/lwjgl/natives/linux/amd64/*",
             "Main", "--headless-mode", "--limithp", "400", "400", "--pyftg-mode"],
            cwd=root, stdout=log, stderr=subprocess.STDOUT,
            env={**os.environ, "SERVER_HOST": "127.0.0.1"})
        try:
            until = time.monotonic() + 30
            while "Waiting to launch a game" not in (evidence / "engine.log").read_text(errors="replace"):
                if proc.poll() is not None or time.monotonic() >= until:
                    raise RuntimeError("native startup failed; inspect engine.log")
                time.sleep(.05)
            connections = {}
            for side, player in players.items():
                native = stack.enter_context(socket.create_connection(("127.0.0.1", PORT), timeout=20))
                native.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                native.sendall(b"\1")
                request = InitializeRequest(player_number=side == 1, player_name=names[side-1], is_blind=False)
                send(native, request.SerializeToString())
                connections[side] = (native, player)
            control = stack.enter_context(socket.create_connection(("127.0.0.1", PORT), timeout=10))
            control.sendall(b"\2")
            request = RunGameRequest(character_1=character, character_2=character,
                                     player_1=names[0], player_2=names[1], game_number=1)
            send(control, request.SerializeToString())
            reply = RunGameResponse.FromString(packet(control))
            if reply.status_code != 0:
                raise RuntimeError(f"native match rejected: {reply.response_message}")
            with ThreadPoolExecutor() as threads:
                futures = {side: threads.submit(relay, *pair, audio=audio) for side, pair in connections.items()}
                try:
                    control.settimeout(2)
                    until = time.monotonic() + 280
                    while True:
                        try:
                            if receive(control, 1) != b"\0":
                                raise RuntimeError("unexpected completion message")
                            break
                        except TimeoutError:
                            if (proc.poll() is not None or time.monotonic() >= until
                                    or 'Exception in thread "main"' in
                                    (evidence / "engine.log").read_text(errors="replace")):
                                raise RuntimeError("native match failed or timed out; inspect engine.log")
                    callbacks = {side: future.result(timeout=25) for side, future in futures.items()}
                finally:
                    # Release blocking relays before joining their threads on a broken game.
                    for side, future in futures.items():
                        if not future.done():
                            connections[side][0].shutdown(socket.SHUT_RDWR)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    points, = (root / "log/point").glob("*.csv")
    style, = (root / "log/style").glob("*.csv")
    native = read_match(match["track"], points, style)
    (evidence / "match-result.json").write_text(json.dumps({**native, "callbacks": callbacks}, indent=2))


if __name__ == "__main__":
    spec = json.loads(sys.argv[1])
    root = Path("/engine")
    for name in ("FightingICE.jar", "lib", "data"):
        (root / name).symlink_to(Path("/install") / name)
    play(Path("/engine"), Path("/evidence"), spec["match"],
         {int(side): path for side, path in spec["bridges"].items()},
         audio=spec["audio"])
