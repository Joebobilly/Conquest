#!/usr/bin/env python3
"""Tiny terminal client for manual packet testing."""

import argparse
import json
import socket
import sys


def recv_line(sock: socket.socket) -> dict:
    raw = b""
    while not raw.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("Connection closed")
        raw += chunk
    return json.loads(raw.decode())


def send_and_recv(sock: socket.socket, payload: dict) -> dict:
    sock.sendall((json.dumps(payload) + "\n").encode())
    return recv_line(sock)


def main() -> None:
    parser = argparse.ArgumentParser(description="Conquest packet CLI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12345)
    args = parser.parse_args()

    with socket.create_connection((args.host, args.port)) as sock:
        print(json.dumps(recv_line(sock), indent=2))
        print("Enter JSON objects; one per line. Ctrl-D to exit.")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req = json.loads(line)
            resp = send_and_recv(sock, req)
            print(json.dumps(resp, indent=2))


if __name__ == "__main__":
    main()
