"""Network client for the Conquest authoritative server."""

from __future__ import annotations

import socket
from typing import Any

from .protocol import ProtocolError, decode_response, encode_request


class ConquestClient:
    """Thin JSON-over-TCP client for the public Conquest protocol."""

    def __init__(self, host: str = "127.0.0.1", port: int = 12345, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None

    def connect(self) -> dict[str, Any]:
        if self._sock is not None:
            raise RuntimeError("Client is already connected")

        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        return self._recv_message()

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def __enter__(self) -> "ConquestClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def request(self, message_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._send(message_type, payload)
        response = self._recv_message()
        if response.get("type") != "ok":
            raise ProtocolError(f"Unexpected response type: {response.get('type')}")
        return response.get("data", {})

    def ping(self) -> dict[str, Any]:
        return self.request("ping")

    def register(self, username: str, password: str) -> dict[str, Any]:
        return self.request("auth.register", {"username": username, "password": password})

    def login(self, username: str, password: str) -> dict[str, Any]:
        return self.request("auth.login", {"username": username, "password": password})

    def resume(self, token: str) -> dict[str, Any]:
        return self.request("auth.resume", {"token": token})

    def logout(self, token: str) -> dict[str, Any]:
        return self.request("auth.logout", {"token": token})

    def world_meta(self) -> dict[str, Any]:
        return self.request("world.meta")

    def world_state(self) -> dict[str, Any]:
        return self.request("world.state")

    def world_region(
        self,
        *,
        min_x: int = 0,
        min_y: int = 0,
        max_x: int | None = None,
        max_y: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"min_x": min_x, "min_y": min_y}
        if max_x is not None:
            payload["max_x"] = max_x
        if max_y is not None:
            payload["max_y"] = max_y
        return self.request("world.region", payload)

    def claim(self, x: int, y: int, power_cost: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"x": x, "y": y}
        if power_cost is not None:
            payload["power_cost"] = power_cost
        return self.request("action.claim", payload)

    def _send(self, message_type: str, payload: dict[str, Any] | None = None) -> None:
        if self._sock is None:
            raise RuntimeError("Client is not connected")
        self._sock.sendall(encode_request(message_type, payload))

    def _recv_message(self) -> dict[str, Any]:
        if self._sock is None:
            raise RuntimeError("Client is not connected")

        raw = b""
        while not raw.endswith(b"\n"):
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ProtocolError("Connection closed by server")
            raw += chunk
        return decode_response(raw)
