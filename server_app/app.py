import socketserver
import threading
import time
from typing import Any

from . import auth, db
from .config import ServerConfig
from .protocol import ProtocolError, error_message, parse_json_line, success_message
from .world import WorldService


PROTECTED_TYPES = {"world.state", "action.claim", "action.attack", "action.build"}


class ConquestRequestHandler(socketserver.StreamRequestHandler):
    server: "ConquestTCPServer"

    def setup(self) -> None:
        super().setup()
        self.user_id: int | None = None
        self.username: str | None = None

    def handle(self) -> None:
        self.wfile.write(
            success_message(
                "hello",
                message="Conquest authoritative server ready",
                protocol_version=self.server.config.protocol_version,
            )
        )
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            request_id = None
            try:
                request = parse_json_line(raw)
                request_id = request.get("request_id")
                response = self.server.dispatch(self, request)
                self.wfile.write(success_message("ok", request_id=request_id, request_type=request["type"], data=response))
            except ProtocolError as exc:
                self.wfile.write(error_message(exc.code, exc.message, request_id=request_id, details=exc.details))
            except Exception as exc:  # noqa: BLE001
                self.wfile.write(error_message("internal_error", str(exc), request_id=request_id))


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
        req_version = int(request.get("protocol_version", self.config.protocol_version))
        if req_version != self.config.protocol_version:
            raise ProtocolError("bad_protocol_version", "Unsupported protocol_version", {"expected": self.config.protocol_version, "got": req_version})

        with self.db_lock:
            with db.connect(self.config.db_path) as conn:
                world = WorldService(
                    conn,
                    default_power=self.config.default_power,
                    max_power=self.config.max_power,
                    power_regen_per_tick=self.config.power_regen_per_tick,
                    tick_seconds=self.config.tick_seconds,
                )
                self._authenticate_request(handler, conn, request)

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
                    return {
                        "tiles": world.world_region(
                            min_x=int(payload.get("min_x", 0)),
                            min_y=int(payload.get("min_y", 0)),
                            max_x=payload.get("max_x"),
                            max_y=payload.get("max_y"),
                        ),
                        "world_version": world.get_world_meta()["version"],
                    }
                if msg_type == "world.patch_since":
                    return world.patches_since(int(payload.get("from_version", 0)))
                if msg_type == "action.claim":
                    self._require_auth(handler)
                    return world.claim_tile(handler.user_id, int(payload["x"]), int(payload["y"]), power_cost=int(payload.get("power_cost", 5)))
                if msg_type == "action.attack":
                    self._require_auth(handler)
                    return world.attack_tile(handler.user_id, int(payload["x"]), int(payload["y"]), power_cost=int(payload.get("power_cost", 15)))
                if msg_type == "action.build":
                    self._require_auth(handler)
                    return world.build_on_tile(
                        handler.user_id,
                        int(payload["x"]),
                        int(payload["y"]),
                        building_type=str(payload["building_type"]),
                        power_cost=int(payload.get("power_cost", 10)),
                    )
                if msg_type == "ping":
                    return {"pong": True, "protocol_version": self.config.protocol_version}
                raise ProtocolError("unknown_type", f"Unknown message type: {msg_type}")

    def _register(self, conn, world: WorldService, payload: dict[str, Any]) -> dict[str, Any]:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        if len(username) < 3:
            raise ProtocolError("invalid_username", "Username must be at least 3 characters")
        if len(password) < 8:
            raise ProtocolError("invalid_password", "Password must be at least 8 characters")

        hashed = auth.hash_password(password)
        try:
            cursor = conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
        except Exception as exc:
            raise ProtocolError("register_failed", "Could not register user", {"reason": str(exc)}) from exc

        user_id = int(cursor.lastrowid)
        world.create_user_resources(user_id)
        spawn_x, spawn_y = world.spawn_for_user_if_needed(user_id)
        conn.commit()
        return {"username": username, "spawn": {"x": spawn_x, "y": spawn_y}}

    def _login(self, handler: ConquestRequestHandler, conn, payload: dict[str, Any]) -> dict[str, Any]:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        row = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if row is None or not auth.verify_password(password, row["password_hash"]):
            raise ProtocolError("invalid_credentials", "Invalid username or password")

        token = auth.new_session_token()
        now = time.time()
        expires_at = now + self.config.session_ttl_seconds
        conn.execute("INSERT INTO sessions (token, user_id, created_at, expires_at, revoked_at) VALUES (?, ?, ?, ?, NULL)", (token, row["id"], now, expires_at))
        conn.commit()

        handler.user_id = int(row["id"])
        handler.username = username
        return {"token": token, "expires_at": expires_at, "user_id": handler.user_id, "username": username}

    def _resume(self, handler: ConquestRequestHandler, conn, payload: dict[str, Any]) -> dict[str, Any]:
        token = str(payload.get("token", ""))
        user = self._resolve_token(conn, token)
        handler.user_id = int(user["id"])
        handler.username = user["username"]
        return {"user_id": handler.user_id, "username": handler.username}

    def _resolve_token(self, conn, token: str):
        if not token:
            raise ProtocolError("missing_token", "Session token is required")
        now = time.time()
        row = conn.execute(
            """
            SELECT users.id, users.username
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
              AND sessions.revoked_at IS NULL
              AND sessions.expires_at > ?
            """,
            (token, now),
        ).fetchone()
        if row is None:
            raise ProtocolError("invalid_session", "Invalid or expired session token")
        return row

    def _authenticate_request(self, handler: ConquestRequestHandler, conn, request: dict[str, Any]) -> None:
        msg_type = request["type"]
        if msg_type not in PROTECTED_TYPES:
            return
        if handler.user_id is not None:
            return
        token = request.get("token")
        if token is None:
            token = (request.get("payload") or {}).get("token")
        if token is None:
            raise ProtocolError("auth_required", "Authentication required for this message type")
        user = self._resolve_token(conn, str(token))
        handler.user_id = int(user["id"])
        handler.username = user["username"]

    @staticmethod
    def _require_auth(handler: ConquestRequestHandler) -> None:
        if handler.user_id is None:
            raise ProtocolError("auth_required", "Authentication required")


def run_server(config: ServerConfig) -> None:
    server = ConquestTCPServer(config)
    print(f"[CONQUEST] Server listening on {config.host}:{config.port}")
    with server:
        server.serve_forever()
