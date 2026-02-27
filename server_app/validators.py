from typing import Any


def _as_non_empty_str(payload: dict[str, Any], key: str) -> str:
    if key not in payload:
        raise ValueError(f"Missing '{key}'")
    value = str(payload[key]).strip()
    if not value:
        raise ValueError(f"'{key}' cannot be empty")
    return value


def _as_int(payload: dict[str, Any], key: str, *, minimum: int | None = None, default: int | None = None) -> int:
    if key not in payload:
        if default is not None:
            return default
        raise ValueError(f"Missing '{key}'")
    try:
        value = int(payload[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{key}' must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"'{key}' must be >= {minimum}")
    return value


def _as_optional_int(payload: dict[str, Any], key: str) -> int | None:
    if key not in payload or payload[key] is None:
        return None
    try:
        return int(payload[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{key}' must be an integer") from exc


def validate_auth_register(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "username": _as_non_empty_str(payload, "username"),
        "password": _as_non_empty_str(payload, "password"),
    }


def validate_auth_login(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "username": _as_non_empty_str(payload, "username"),
        "password": _as_non_empty_str(payload, "password"),
    }


def validate_auth_resume(payload: dict[str, Any]) -> dict[str, str]:
    return {"token": _as_non_empty_str(payload, "token")}


def validate_world_region(payload: dict[str, Any]) -> dict[str, int | None]:
    return {
        "min_x": _as_int(payload, "min_x", default=0),
        "min_y": _as_int(payload, "min_y", default=0),
        "max_x": _as_optional_int(payload, "max_x"),
        "max_y": _as_optional_int(payload, "max_y"),
    }


def validate_action_claim(payload: dict[str, Any]) -> dict[str, int]:
    result = {
        "x": _as_int(payload, "x"),
        "y": _as_int(payload, "y"),
        "power_cost": 5,
    }
    if "power_cost" in payload:
        result["power_cost"] = _as_int(payload, "power_cost", minimum=1)
    return result
