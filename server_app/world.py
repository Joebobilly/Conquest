import json
import time
from typing import Any

from .protocol import ProtocolError


class WorldService:
    def __init__(self, conn, default_power: int, max_power: int, power_regen_per_tick: int, tick_seconds: float):
        self.conn = conn
        self.default_power = default_power
        self.max_power = max_power
        self.power_regen_per_tick = power_regen_per_tick
        self.tick_seconds = tick_seconds

    def create_user_resources(self, user_id: int) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO resources (user_id, power, max_power, last_tick) VALUES (?, ?, ?, ?)",
            (user_id, self.default_power, self.max_power, time.time()),
        )

    def tick_user_resources(self, user_id: int) -> None:
        row = self.conn.execute(
            "SELECT power, max_power, last_tick FROM resources WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return
        now = time.time()
        elapsed = now - row["last_tick"]
        ticks = int(elapsed // self.tick_seconds)
        if ticks <= 0:
            return
        new_power = min(row["max_power"], row["power"] + ticks * self.power_regen_per_tick)
        new_last_tick = row["last_tick"] + ticks * self.tick_seconds
        self.conn.execute(
            "UPDATE resources SET power = ?, last_tick = ? WHERE user_id = ?",
            (new_power, new_last_tick, user_id),
        )

    def _spend_power(self, user_id: int, amount: int) -> None:
        if amount < 0:
            raise ProtocolError("invalid_cost", "Cost cannot be negative")
        resources = self.conn.execute("SELECT power FROM resources WHERE user_id=?", (user_id,)).fetchone()
        if resources is None or resources["power"] < amount:
            raise ProtocolError("insufficient_power", "Not enough power")
        self.conn.execute("UPDATE resources SET power = power - ? WHERE user_id = ?", (amount, user_id))

    def spawn_for_user_if_needed(self, user_id: int) -> tuple[int, int]:
        owned = self.conn.execute(
            "SELECT x, y FROM land_tiles WHERE owner_user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        if owned is not None:
            return (owned["x"], owned["y"])

        spot = self.conn.execute(
            "SELECT x, y FROM land_tiles WHERE owner_user_id IS NULL AND terrain='land' ORDER BY y, x LIMIT 1"
        ).fetchone()
        if spot is None:
            raise ProtocolError("spawn_failed", "No spawnable land tile available")

        self.conn.execute(
            "UPDATE land_tiles SET owner_user_id = ? WHERE x = ? AND y = ?",
            (user_id, spot["x"], spot["y"]),
        )
        version = self._next_world_version()
        self._record_event(user_id, "tile.claim", {"x": spot["x"], "y": spot["y"], "owner_user_id": user_id}, version)
        return (spot["x"], spot["y"])

    def get_world_meta(self) -> dict[str, int]:
        row = self.conn.execute("SELECT width, height, version FROM world_meta WHERE id=1").fetchone()
        return {"width": row["width"], "height": row["height"], "version": row["version"]}

    def get_user_state(self, user_id: int) -> dict[str, Any]:
        self.tick_user_resources(user_id)
        self.conn.commit()

        resources = self.conn.execute(
            "SELECT power, max_power FROM resources WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        tiles = self.conn.execute(
            "SELECT x, y FROM land_tiles WHERE owner_user_id = ? ORDER BY y, x",
            (user_id,),
        ).fetchall()
        return {
            "resources": {"power": resources["power"], "max_power": resources["max_power"]},
            "owned_tiles": [{"x": t["x"], "y": t["y"]} for t in tiles],
            "world_version": self.get_world_meta()["version"],
        }

    def _is_adjacent_to_owner(self, user_id: int, x: int, y: int) -> bool:
        checks = [(x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)]
        for cx, cy in checks:
            row = self.conn.execute("SELECT owner_user_id FROM land_tiles WHERE x=? AND y=?", (cx, cy)).fetchone()
            if row is not None and row["owner_user_id"] == user_id:
                return True
        return False

    def _get_tile(self, x: int, y: int):
        tile = self.conn.execute("SELECT owner_user_id, terrain FROM land_tiles WHERE x=? AND y=?", (x, y)).fetchone()
        if tile is None:
            raise ProtocolError("tile_oob", "Tile out of bounds", {"x": x, "y": y})
        return tile

    def _next_world_version(self) -> int:
        self.conn.execute(
            "UPDATE world_meta SET version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE id=1"
        )
        row = self.conn.execute("SELECT version FROM world_meta WHERE id=1").fetchone()
        return int(row["version"])

    def _record_event(self, actor_user_id: int | None, event_type: str, payload: dict[str, Any], version: int) -> None:
        self.conn.execute(
            "INSERT INTO world_events (version, actor_user_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (version, actor_user_id, event_type, json.dumps(payload, separators=(",", ":")), time.time()),
        )

    def claim_tile(self, user_id: int, x: int, y: int, power_cost: int = 5) -> dict[str, Any]:
        self.tick_user_resources(user_id)
        tile = self._get_tile(x, y)
        if tile["terrain"] != "land":
            raise ProtocolError("invalid_tile", "Tile cannot be claimed")
        if tile["owner_user_id"] == user_id:
            raise ProtocolError("already_owned", "Tile already owned by you")
        if tile["owner_user_id"] is not None:
            raise ProtocolError("occupied", "Tile already owned")
        if not self._is_adjacent_to_owner(user_id, x, y):
            raise ProtocolError("not_adjacent", "Tile must be cardinal-adjacent to owned land")

        self._spend_power(user_id, power_cost)
        self.conn.execute("UPDATE land_tiles SET owner_user_id = ? WHERE x = ? AND y = ?", (user_id, x, y))
        version = self._next_world_version()
        self._record_event(user_id, "tile.claim", {"x": x, "y": y, "owner_user_id": user_id}, version)
        self.conn.commit()
        state = self.get_user_state(user_id)
        return {"claimed": {"x": x, "y": y}, "power_cost": power_cost, "resources": state["resources"], "world_version": version}

    def attack_tile(self, user_id: int, x: int, y: int, power_cost: int = 15) -> dict[str, Any]:
        self.tick_user_resources(user_id)
        tile = self._get_tile(x, y)
        owner = tile["owner_user_id"]
        if owner is None:
            raise ProtocolError("neutral_tile", "Use action.claim for neutral tiles")
        if owner == user_id:
            raise ProtocolError("already_owned", "Tile already owned by you")
        if not self._is_adjacent_to_owner(user_id, x, y):
            raise ProtocolError("not_adjacent", "Tile must be cardinal-adjacent to owned land")

        self._spend_power(user_id, power_cost)
        self.conn.execute("UPDATE land_tiles SET owner_user_id = ? WHERE x = ? AND y = ?", (user_id, x, y))
        self.conn.execute("DELETE FROM buildings WHERE x = ? AND y = ?", (x, y))
        version = self._next_world_version()
        self._record_event(
            user_id,
            "tile.attack_capture",
            {"x": x, "y": y, "from_owner_user_id": owner, "to_owner_user_id": user_id},
            version,
        )
        self.conn.commit()
        state = self.get_user_state(user_id)
        return {"captured": {"x": x, "y": y}, "power_cost": power_cost, "resources": state["resources"], "world_version": version}

    def build_on_tile(self, user_id: int, x: int, y: int, building_type: str, power_cost: int = 10) -> dict[str, Any]:
        self.tick_user_resources(user_id)
        tile = self._get_tile(x, y)
        if tile["owner_user_id"] != user_id:
            raise ProtocolError("not_owner", "Can only build on your own tile")
        existing = self.conn.execute("SELECT x FROM buildings WHERE x=? AND y=?", (x, y)).fetchone()
        if existing is not None:
            raise ProtocolError("building_exists", "Building already exists on tile")

        self._spend_power(user_id, power_cost)
        self.conn.execute(
            "INSERT INTO buildings (x, y, owner_user_id, building_type, level) VALUES (?, ?, ?, ?, 1)",
            (x, y, user_id, building_type),
        )
        version = self._next_world_version()
        self._record_event(user_id, "building.place", {"x": x, "y": y, "building_type": building_type, "level": 1}, version)
        self.conn.commit()
        state = self.get_user_state(user_id)
        return {"built": {"x": x, "y": y, "building_type": building_type}, "power_cost": power_cost, "resources": state["resources"], "world_version": version}

    def world_region(self, min_x: int = 0, min_y: int = 0, max_x: int | None = None, max_y: int | None = None):
        meta = self.get_world_meta()
        if max_x is None:
            max_x = meta["width"] - 1
        if max_y is None:
            max_y = meta["height"] - 1
        rows = self.conn.execute(
            """
            SELECT t.x, t.y, t.owner_user_id, t.terrain, b.building_type, b.level
            FROM land_tiles t
            LEFT JOIN buildings b ON b.x=t.x AND b.y=t.y
            WHERE t.x BETWEEN ? AND ? AND t.y BETWEEN ? AND ?
            ORDER BY t.y, t.x
            """,
            (min_x, max_x, min_y, max_y),
        ).fetchall()
        return [
            {
                "x": r["x"], "y": r["y"], "terrain": r["terrain"], "owner_user_id": r["owner_user_id"],
                "building": None if r["building_type"] is None else {"type": r["building_type"], "level": r["level"]},
            }
            for r in rows
        ]

    def patches_since(self, from_version: int) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT version, actor_user_id, event_type, payload_json, created_at FROM world_events WHERE version > ? ORDER BY version",
            (from_version,),
        ).fetchall()
        return {
            "from_version": from_version,
            "to_version": self.get_world_meta()["version"],
            "events": [
                {
                    "version": r["version"],
                    "actor_user_id": r["actor_user_id"],
                    "event_type": r["event_type"],
                    "payload": json.loads(r["payload_json"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ],
        }
