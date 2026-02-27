import argparse

from .app import run_server
from .config import ServerConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Conquest authoritative server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=12345)
    parser.add_argument("--db", default="data/conquest.db")
    parser.add_argument("--width", type=int, default=100)
    parser.add_argument("--height", type=int, default=100)
    parser.add_argument("--session-ttl", type=int, default=60 * 60 * 24 * 7)
    args = parser.parse_args()

    config = ServerConfig(
        host=args.host,
        port=args.port,
        db_path=args.db,
        world_width=args.width,
        world_height=args.height,
        session_ttl_seconds=args.session_ttl,
    )
    run_server(config)


if __name__ == "__main__":
    main()
