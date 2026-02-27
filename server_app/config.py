from dataclasses import dataclass


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 12345
    db_path: str = "data/conquest.db"
    world_width: int = 100
    world_height: int = 100
    default_power: int = 100
    max_power: int = 100
    power_regen_per_tick: int = 1
    tick_seconds: float = 2.0
    session_ttl_seconds: int = 60 * 60 * 24 * 7
