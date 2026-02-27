import socketserver
import threading
import time
from typing import Any

from . import auth, db
from .config import ServerConfig
from .protocol import parse_json_line, serialize_message
from .validators import (
    validate_action_claim,
    validate_auth_login,
    validate_auth_register,
    validate_auth_resume,
    validate_world_region,
)
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
        with db.connect(config.db_path) as conn:
            self._cleanup_expired_sessions(conn)
        super().__init__((config.host, config.port), ConquestRequestHandler)

    def dispatch(self, handler: ConquestRequestHandler, request: dict[str, Any]) -> dict[str, Any]:
        msg_type = request["type"]
        payload = request.get("payload", {}) or {}

        with self.db_lock:
            with db.connect(self.config.db_path) as conn:
                if msg_type != "auth.resume":
                    self._cleanup_expired_sessions(conn)
                world = WorldService(
                    conn,
                    default_power=self.config.default_power,
                    max_power=self.config.max_power,
                    power_regen_per_tick=self.config.power_regen_per_tick,
                    tick_seconds=self.config.tick_seconds,
                )

                if msg_type == "auth.register":
                    return self._register(conn, world, validate_auth_register(payload))
                if msg_type == "auth.login":
                    return self._login(handler, conn, validate_auth_login(payload))
                if msg_type == "auth.resume":
                    return self._resume(handler, conn, validate_auth_resume(payload))
                if msg_type == "auth.logout":
                    return self._logout(handler, conn, validate_auth_resume(payload))
                if msg_type == "world.meta":
                    return world.get_world_meta()
                if msg_type == "world.state":
                    self._require_auth(handler)
                    return world.get_user_state(handler.user_id)
                if msg_type == "world.region":
                    region = validate_world_region(payload)
                    return {"tiles": world.world_patch_since(**region)}
                if msg_type == "action.claim":
                    self._require_auth(handler)
                    claim = validate_action_claim(payload)
                    return world.claim_tile(
                        handler.user_id,
                        claim["x"],
                        claim["y"],
                        power_cost=claim["power_cost"],
                    )
                if msg_type == "ping":
                    return {"pong": True}
                raise ValueError(f"Unknown message type: {msg_type}")

    def _register(self, conn, world: WorldService, payload: dict[str, Any]) -> dict[str, Any]:
        username = payload["username"].strip()
        password = payload["password"]
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
        username = payload["username"].strip()
        password = payload["password"]
        row = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if row is None or not auth.verify_password(password, row["password_hash"]):
            raise ValueError("Invalid username or password")

        token = auth.new_session_token()
        now = time.time()
        expires_at = now + self.config.session_ttl_seconds
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, row["id"], now, expires_at),
        )
        conn.commit()

        handler.user_id = int(row["id"])
        handler.username = username
        return {
            "token": token,
            "user_id": handler.user_id,
            "username": username,
            "expires_at": expires_at,
        }

    def _resume(self, handler: ConquestRequestHandler, conn, payload: dict[str, Any]) -> dict[str, Any]:
        token = payload["token"]
        row = conn.execute(
            "SELECT users.id, users.username, sessions.expires_at FROM sessions JOIN users ON users.id = sessions.user_id WHERE sessions.token = ?",
            (token,),
        ).fetchone()
        if row is None:
            raise ValueError("Invalid session token")
        if row["expires_at"] <= time.time():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            raise ValueError("Session token expired")

        handler.user_id = int(row["id"])
        handler.username = row["username"]
        return {"user_id": handler.user_id, "username": handler.username}

    def _logout(self, handler: ConquestRequestHandler, conn, payload: dict[str, Any]) -> dict[str, Any]:
        token = payload["token"]
        deleted = conn.execute("DELETE FROM sessions WHERE token = ?", (token,)).rowcount
        conn.commit()
        if handler.user_id is not None:
            handler.user_id = None
            handler.username = None
        if deleted == 0:
            raise ValueError("Invalid session token")
        return {"logged_out": True}

    @staticmethod
    def _require_auth(handler: ConquestRequestHandler) -> None:
        if handler.user_id is None:
            raise ValueError("Authentication required")

    @staticmethod
    def _cleanup_expired_sessions(conn) -> None:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (time.time(),))
        conn.commit()


def run_server(config: ServerConfig) -> None:
    server = ConquestTCPServer(config)
    print(f"[CONQUEST] Server listening on {config.host}:{config.port}")
    with server:
        server.serve_forever()
