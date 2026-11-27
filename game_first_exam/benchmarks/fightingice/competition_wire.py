"""Native player packets over a player-only Unix socket; no engine control RPCs."""
import argparse
import socket
import time


def receive(sock, size):
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise EOFError("player socket closed")
        data.extend(chunk)
    return bytes(data)


def packet(sock, maximum=2**22):
    size = int.from_bytes(receive(sock, 4), "little")
    if size > maximum:
        raise ValueError("oversized player packet")
    return receive(sock, size)


def send(sock, payload):
    sock.sendall(len(payload).to_bytes(4, "little") + payload)


def public_state(native, *, audio=True):
    from pyftg.models.enums.flag import Flag
    from pyftg.protoc.service_pb2 import PlayerGameState

    allowed = {
        Flag.INITIALIZE: ("game_data",),
        Flag.PROCESSING: ("frame_data", "audio_data") if audio else ("frame_data",),
        Flag.ROUND_END: ("round_result",),
        Flag.GAME_END: ("round_result",),
    }
    flag = Flag(native.state_flag)
    state = PlayerGameState(state_flag=flag.value)
    for field in allowed[flag]:
        if native.HasField(field):
            getattr(state, field).CopyFrom(getattr(native, field))
    if flag == Flag.PROCESSING:
        state.is_control = native.is_control
    # Rebuild rather than forwarding extra top-level fields or protobuf unknowns.
    state.DiscardUnknownFields()
    return flag, state


def controller(path, side):
    from controller import AI
    from pyftg import AudioData, FrameData, GameData, Key, RoundResult
    from pyftg.models.enums.flag import Flag
    from pyftg.protoc.service_pb2 import PlayerGameState
    from pyftg.utils.protobuf import convert_key_to_proto

    ai = AI()
    with socket.socket(socket.AF_UNIX) as sock:
        until = time.monotonic() + 45
        while True:
            try:
                sock.connect(path)
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if time.monotonic() >= until:
                    raise
                time.sleep(.05)
        try:
            while True:
                tag = receive(sock, 1)
                if tag == b"\0":
                    break
                if tag != b"\1":
                    raise ValueError("unknown player event")
                state = PlayerGameState.FromString(packet(sock))
                flag = Flag(state.state_flag)
                if flag == Flag.INITIALIZE:
                    ai.initialize(GameData.from_proto(state.game_data), side == 1)
                elif flag == Flag.PROCESSING:
                    ai.get_information(FrameData.from_proto(state.frame_data), state.is_control)
                    if state.HasField("audio_data"):
                        ai.get_audio_data(AudioData.from_proto(state.audio_data))
                    ai.processing()
                    key = ai.input()
                    if not isinstance(key, Key):
                        raise TypeError("AI.input() must return pyftg.Key")
                    send(sock, convert_key_to_proto(key).SerializeToString())
                else:
                    ai.round_end(RoundResult.from_proto(state.round_result))
                    if flag == Flag.GAME_END:
                        ai.game_end()
        finally:
            ai.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("socket")
    parser.add_argument("side", type=int, choices=(1, 2))
    args = parser.parse_args()
    controller(args.socket, args.side)
