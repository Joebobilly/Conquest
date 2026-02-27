#!/usr/bin/env python3
"""Interactive standalone client for Conquest protocol testing and gameplay basics."""

from __future__ import annotations

import argparse
import json

from .connection import ConquestClient


HELP_TEXT = """
Commands:
  register <username> <password>
  login <username> <password>
  resume <token>
  logout [token]           # token defaults to latest login token
  ping
  world.meta
  world.state
  world.region <min_x> <min_y> [max_x] [max_y]
  world.grid               # render entire known map as ASCII grid
  claim <x> <y> [power_cost]
  raw <json-packet>        # send packet by explicit message type/payload
  token                    # print saved token
  help
  quit / exit
""".strip()


def _tile_to_ascii(tile: dict) -> str:
    owner_id = tile.get("owner_user_id")
    if owner_id is not None:
        return str(owner_id)
    if tile.get("terrain") == "water":
        return "-"
    return "0"


def render_world_grid(meta: dict, tiles: list[dict]) -> str:
    width = int(meta["width"])
    height = int(meta["height"])
    tile_lookup = {(tile["x"], tile["y"]): tile for tile in tiles}

    rows = []
    for y in range(height):
        chars = []
        for x in range(width):
            tile = tile_lookup.get((x, y), {"terrain": "water", "owner_user_id": None})
            chars.append(_tile_to_ascii(tile))
        rows.append("".join(chars))
    return "\n".join(rows)


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Conquest standalone client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12345)
    args = parser.parse_args()

    client = ConquestClient(host=args.host, port=args.port)
    hello = client.connect()
    session_token: str | None = None

    print("Connected.")
    _print_json(hello)
    print(HELP_TEXT)

    try:
        while True:
            try:
                line = input("conquest> ").strip()
            except EOFError:
                print()
                break

            if not line:
                continue
            if line in {"quit", "exit"}:
                break
            if line == "help":
                print(HELP_TEXT)
                continue
            if line == "token":
                print(session_token or "(none)")
                continue

            parts = line.split()
            cmd = parts[0]

            try:
                if cmd == "register" and len(parts) == 3:
                    _print_json(client.register(parts[1], parts[2]))
                elif cmd == "login" and len(parts) == 3:
                    result = client.login(parts[1], parts[2])
                    session_token = result.get("token")
                    _print_json(result)
                elif cmd == "resume" and len(parts) == 2:
                    _print_json(client.resume(parts[1]))
                    session_token = parts[1]
                elif cmd == "logout" and len(parts) in {1, 2}:
                    token = parts[1] if len(parts) == 2 else session_token
                    if token is None:
                        raise ValueError("No token available. Use: logout <token>")
                    _print_json(client.logout(token))
                    if token == session_token:
                        session_token = None
                elif cmd == "ping" and len(parts) == 1:
                    _print_json(client.ping())
                elif cmd == "world.meta" and len(parts) == 1:
                    _print_json(client.world_meta())
                elif cmd == "world.state" and len(parts) == 1:
                    _print_json(client.world_state())
                elif cmd == "world.region" and len(parts) in {3, 5}:
                    min_x = int(parts[1])
                    min_y = int(parts[2])
                    if len(parts) == 3:
                        _print_json(client.world_region(min_x=min_x, min_y=min_y))
                    else:
                        _print_json(
                            client.world_region(
                                min_x=min_x,
                                min_y=min_y,
                                max_x=int(parts[3]),
                                max_y=int(parts[4]),
                            )
                        )
                elif cmd == "world.grid" and len(parts) == 1:
                    meta = client.world_meta()
                    region = client.world_region(
                        min_x=0,
                        min_y=0,
                        max_x=int(meta["width"]) - 1,
                        max_y=int(meta["height"]) - 1,
                    )
                    print(render_world_grid(meta, region.get("tiles", [])))
                elif cmd == "claim" and len(parts) in {3, 4}:
                    x, y = int(parts[1]), int(parts[2])
                    power_cost = int(parts[3]) if len(parts) == 4 else None
                    _print_json(client.claim(x, y, power_cost))
                elif cmd == "raw":
                    packet = json.loads(line[len("raw ") :])
                    if not isinstance(packet, dict) or "type" not in packet:
                        raise ValueError("Raw packet must be a JSON object with 'type'")
                    _print_json(client.request(packet["type"], packet.get("payload")))
                else:
                    print("Unknown command. Type 'help'.")
            except Exception as exc:  # noqa: BLE001 - keep CLI resilient
                print(f"error: {exc}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
