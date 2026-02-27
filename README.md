# Conquest (Server-First Rewrite)

This repository now starts from an **authoritative server** foundation for a persistent Conquest world.

## Goals of this rewrite

- Server is source of truth for world state.
- Terminal packet testing works before any UI client work.
- Clean protocol and project structure for community-made clients.

## Current project structure

- `server_app/`: authoritative TCP+JSON server.
- `scripts/packet_cli.py`: tiny terminal client for manual packet testing.
- `tests/`: protocol and world rule tests.
- Legacy prototype folders (`ConquestTest2/`, `SOCKETTEST/`) are kept for historical reference.

## Run the server

```bash
python -m server_app --host 0.0.0.0 --port 12345 --db data/conquest.db --width 100 --height 100 --session-ttl 604800
```

## Packet protocol (newline-delimited JSON)

All messages are JSON objects with `type` and optional `payload`.

### Register

```json
{"type":"auth.register","payload":{"username":"alice","password":"supersecret"}}
```

### Login

```json
{"type":"auth.login","payload":{"username":"alice","password":"supersecret"}}
```

### Resume session

```json
{"type":"auth.resume","payload":{"token":"..."}}
```

### Logout

```json
{"type":"auth.logout","payload":{"token":"..."}}
```

### Get user state (requires auth)

```json
{"type":"world.state"}
```

### Claim neutral land tile (requires auth)

```json
{"type":"action.claim","payload":{"x":10,"y":3}}
```

### Fetch world region

```json
{"type":"world.region","payload":{"min_x":0,"min_y":0,"max_x":20,"max_y":20}}
```

## Terminal testing

```bash
python scripts/packet_cli.py --host 127.0.0.1 --port 12345
```

Then paste JSON requests one-per-line.

## What is intentionally in-scope right now

- Account registration/login, expiring session tokens, and logout.
- Authoritative land ownership state in SQLite.
- Power resource and regeneration.
- Adjacency rule for claiming neutral land.

## What is intentionally out-of-scope for this first step

- Co-op/factions, attacks on enemy land, buildings, walls, diplomacy.
- TLS transport, advanced anti-cheat, and production deployment hardening.

Those systems should be layered on top of this server-first base.
