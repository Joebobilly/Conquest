import json
from typing import Any


def parse_json_line(line: bytes) -> dict[str, Any]:
    try:
        decoded = line.decode().strip()
        if not decoded:
            raise ValueError("Empty payload")
        data = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object")
    if "type" not in data:
        raise ValueError("Message missing 'type'")
    return data


def serialize_message(message_type: str, **payload: Any) -> bytes:
    data = {"type": message_type, **payload}
    return (json.dumps(data, separators=(",", ":")) + "\n").encode()
