import time
from typing import Any


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
            raise ValueError("No spawnable land tile available")

        self.conn.execute(
            "UPDATE land_tiles SET owner_user_id = ? WHERE x = ? AND y = ?",
            (user_id, spot["x"], spot["y"]),
        )
        return (spot["x"], spot["y"])

    def get_world_meta(self) -> dict[str, int]:
        row = self.conn.execute("SELECT width, height FROM world_meta WHERE id=1").fetchone()
        return {"width": row["width"], "height": row["height"]}

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
        }

    def _is_adjacent_to_owner(self, user_id: int, x: int, y: int) -> bool:
        checks = [(x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)]
        for cx, cy in checks:
            row = self.conn.execute(
                "SELECT owner_user_id FROM land_tiles WHERE x=? AND y=?",
                (cx, cy),
            ).fetchone()
            if row is not None and row["owner_user_id"] == user_id:
                return True
        return False

    def claim_tile(self, user_id: int, x: int, y: int, power_cost: int = 5) -> dict[str, Any]:
        self.tick_user_resources(user_id)

        tile = self.conn.execute(
            "SELECT owner_user_id, terrain FROM land_tiles WHERE x=? AND y=?",
            (x, y),
        ).fetchone()
        if tile is None:
            raise ValueError("Tile out of bounds")
        if tile["terrain"] != "land":
            raise ValueError("Tile cannot be claimed")
        if tile["owner_user_id"] == user_id:
            raise ValueError("Tile already owned by you")
        if tile["owner_user_id"] is not None:
            raise ValueError("Tile already owned")
        if not self._is_adjacent_to_owner(user_id, x, y):
            raise ValueError("Tile must be cardinal-adjacent to owned land")

        resources = self.conn.execute(
            "SELECT power FROM resources WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if resources is None or resources["power"] < power_cost:
            raise ValueError("Not enough power")

        self.conn.execute(
            "UPDATE resources SET power = power - ? WHERE user_id = ?",
            (power_cost, user_id),
        )
        self.conn.execute(
            "UPDATE land_tiles SET owner_user_id = ? WHERE x = ? AND y = ?",
            (user_id, x, y),
        )
        self.conn.commit()

        state = self.get_user_state(user_id)
        return {
            "claimed": {"x": x, "y": y},
            "power_cost": power_cost,
            "resources": state["resources"],
        }

    def world_patch_since(self, min_x: int = 0, min_y: int = 0, max_x: int | None = None, max_y: int | None = None):
        meta = self.get_world_meta()
        if max_x is None:
            max_x = meta["width"] - 1
        if max_y is None:
            max_y = meta["height"] - 1

        rows = self.conn.execute(
            """
            SELECT x, y, owner_user_id, terrain
            FROM land_tiles
            WHERE x BETWEEN ? AND ? AND y BETWEEN ? AND ?
            ORDER BY y, x
            """,
            (min_x, max_x, min_y, max_y),
        ).fetchall()

        return [
            {
                "x": r["x"],
                "y": r["y"],
                "terrain": r["terrain"],
                "owner_user_id": r["owner_user_id"],
            }
            for r in rows
        ]
