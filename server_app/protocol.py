import json
from typing import Any


class ProtocolError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def parse_json_line(line: bytes) -> dict[str, Any]:
    try:
        decoded = line.decode().strip()
        if not decoded:
            raise ProtocolError("empty_payload", "Empty payload")
        data = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ProtocolError("invalid_json", f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ProtocolError("invalid_message", "Message must be a JSON object")
    if "type" not in data:
        raise ProtocolError("missing_type", "Message missing 'type'")
    if "request_id" in data and not isinstance(data["request_id"], str):
        raise ProtocolError("invalid_request_id", "request_id must be a string")
    return data


def success_message(message_type: str, request_id: str | None = None, **payload: Any) -> bytes:
    data = {"type": message_type, **payload}
    if request_id is not None:
        data["request_id"] = request_id
    return (json.dumps(data, separators=(",", ":")) + "\n").encode()


def error_message(code: str, message: str, request_id: str | None = None, details: dict[str, Any] | None = None) -> bytes:
    data = {
        "type": "error",
        "code": code,
        "message": message,
        "details": details or {},
    }
    if request_id is not None:
        data["request_id"] = request_id
    return (json.dumps(data, separators=(",", ":")) + "\n").encode()
