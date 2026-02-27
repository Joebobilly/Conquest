import socketserver
import threading
from typing import Any

from . import auth, db
from .config import ServerConfig
from .protocol import parse_json_line, serialize_message
from .world import WorldService


class ConquestRequestHandler(socketserver.StreamRequestHandler):
    server: "ConquestTCPServer"

    def setup(self) -> None:
        super().setup()
        self.user_id: int | None = None
        self.username: str | None = None

    def handle(self) -> None:
        self.wfile.write(serialize_message("hello", message="Conquest authoritative server ready"))
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            try:
                request = parse_json_line(raw)
                response = self.server.dispatch(self, request)
                self.wfile.write(serialize_message("ok", request_type=request["type"], data=response))
            except Exception as exc:  # noqa: BLE001 - keep protocol errors in-band
                self.wfile.write(serialize_message("error", error=str(exc)))


class ConquestTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, config: ServerConfig):
        self.config = config
        self.db_lock = threading.Lock()
        db.initialize(config.db_path, config.world_width, config.world_height)
        super().__init__((config.host, config.port), ConquestRequestHandler)

    def dispatch(self, handler: ConquestRequestHandler, request: dict[str, Any]) -> dict[str, Any]:
        msg_type = request["type"]
        payload = request.get("payload", {}) or {}

        with self.db_lock:
            with db.connect(self.config.db_path) as conn:
                world = WorldService(
                    conn,
                    default_power=self.config.default_power,
                    max_power=self.config.max_power,
                    power_regen_per_tick=self.config.power_regen_per_tick,
                    tick_seconds=self.config.tick_seconds,
                )

                if msg_type == "auth.register":
                    return self._register(conn, world, payload)
                if msg_type == "auth.login":
                    return self._login(handler, conn, payload)
                if msg_type == "auth.resume":
                    return self._resume(handler, conn, payload)
                if msg_type == "world.meta":
                    return world.get_world_meta()
                if msg_type == "world.state":
                    self._require_auth(handler)
                    return world.get_user_state(handler.user_id)
                if msg_type == "world.region":
                    return {"tiles": world.world_patch_since(
                        min_x=int(payload.get("min_x", 0)),
                        min_y=int(payload.get("min_y", 0)),
                        max_x=payload.get("max_x"),
                        max_y=payload.get("max_y"),
                    )}
                if msg_type == "action.claim":
                    self._require_auth(handler)
                    return world.claim_tile(
                        handler.user_id,
                        int(payload["x"]),
                        int(payload["y"]),
                        power_cost=int(payload.get("power_cost", 5)),
                    )
                if msg_type == "ping":
                    return {"pong": True}
                raise ValueError(f"Unknown message type: {msg_type}")

    def _register(self, conn, world: WorldService, payload: dict[str, Any]) -> dict[str, Any]:
        username = str(payload["username"]).strip()
        password = str(payload["password"])
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        hashed = auth.hash_password(password)
        try:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hashed),
            )
        except Exception as exc:  # sqlite uniqueness message is acceptable here
            raise ValueError(f"Could not register user: {exc}") from exc

        user_id = int(cursor.lastrowid)
        world.create_user_resources(user_id)
        spawn_x, spawn_y = world.spawn_for_user_if_needed(user_id)
        conn.commit()
        return {"username": username, "spawn": {"x": spawn_x, "y": spawn_y}}

    def _login(self, handler: ConquestRequestHandler, conn, payload: dict[str, Any]) -> dict[str, Any]:
        username = str(payload["username"]).strip()
        password = str(payload["password"])
        row = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if row is None or not auth.verify_password(password, row["password_hash"]):
            raise ValueError("Invalid username or password")

        token = auth.new_session_token()
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, row["id"]))
        conn.commit()

        handler.user_id = int(row["id"])
        handler.username = username
        return {"token": token, "user_id": handler.user_id, "username": username}

    def _resume(self, handler: ConquestRequestHandler, conn, payload: dict[str, Any]) -> dict[str, Any]:
        token = str(payload["token"])
        row = conn.execute(
            "SELECT users.id, users.username FROM sessions JOIN users ON users.id = sessions.user_id WHERE sessions.token = ?",
            (token,),
        ).fetchone()
        if row is None:
            raise ValueError("Invalid session token")

        handler.user_id = int(row["id"])
        handler.username = row["username"]
        return {"user_id": handler.user_id, "username": handler.username}

    @staticmethod
    def _require_auth(handler: ConquestRequestHandler) -> None:
        if handler.user_id is None:
            raise ValueError("Authentication required")


def run_server(config: ServerConfig) -> None:
    server = ConquestTCPServer(config)
    print(f"[CONQUEST] Server listening on {config.host}:{config.port}")
    with server:
        server.serve_forever()
