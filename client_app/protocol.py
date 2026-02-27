"""Standalone protocol utilities for Conquest clients.

This module intentionally does not import server code so third-party clients can
copy or reimplement this contract independently.
"""

from __future__ import annotations

import json
from typing import Any


class ProtocolError(RuntimeError):
    """Raised when server response packets are malformed or indicate an error."""


def encode_request(message_type: str, payload: dict[str, Any] | None = None) -> bytes:
    packet: dict[str, Any] = {"type": message_type}
    if payload:
        packet["payload"] = payload
    return (json.dumps(packet, separators=(",", ":")) + "\n").encode()


def decode_response(raw_line: bytes) -> dict[str, Any]:
    try:
        decoded = raw_line.decode().strip()
        if not decoded:
            raise ProtocolError("Empty server response")
        message = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"Invalid server JSON: {exc}") from exc

    if not isinstance(message, dict):
        raise ProtocolError("Server response must be a JSON object")
    if "type" not in message:
        raise ProtocolError("Server response missing 'type'")

    if message["type"] == "error":
        raise ProtocolError(str(message.get("error", "Unknown server error")))

    return message
