"""Public command-line client. No game code is evaluated here."""
import argparse
import http.client
import json
import socket
import sys
from pathlib import Path


class Connection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost", timeout=360)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def request(path, command, payload=None):
    conn = Connection(path)
    try:
        body = None if payload is None else json.dumps(payload).encode()
        conn.request("GET" if body is None else "POST", "/" + command, body,
                     {"Content-Type": "application/json"})
        response = conn.getresponse()
        result = json.load(response)
        if response.status != 200:
            raise ValueError(result.get("error", f"HTTP {response.status}"))
        return result
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "prompt", "observe"):
        commands.add_parser(command)
    step = commands.add_parser("step")
    step.add_argument("number", type=int)
    step.add_argument("file", help="Python source file, or - for stdin")
    args = parser.parse_args()
    payload = None
    if args.command == "step":
        code = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
        payload = {"number": args.number, "code": code}
    print(json.dumps(request("/channel/game.sock", args.command, payload), ensure_ascii=False))
