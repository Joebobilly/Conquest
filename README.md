# Conquest (Server-First Rewrite)

This repository now starts from an **authoritative server** foundation for a persistent Conquest world.

## Goals of this rewrite

- Server is source of truth for world state.
- Terminal packet testing works before any UI client work.
- Clean protocol and project structure for community-made clients.

## Current project structure

- `server_app/`: authoritative TCP+JSON server.
- `scripts/packet_cli.py`: terminal client for manual packet testing.
- `tests/`: protocol and world rule tests.
- Legacy prototype folders (`ConquestTest2/`, `SOCKETTEST/`) are kept for historical reference.

## Run the server

```bash
python3 -m server_app --host 0.0.0.0 --port 12345 --db data/conquest.db --width 100 --height 100
```

## Protocol (newline-delimited JSON)

Message envelope:

```json
{"type":"...","request_id":"...","protocol_version":1,"payload":{}}
```

- `request_id` and `protocol_version` are recommended on every request.
- Responses include either `{"type":"ok", ...}` or `{"type":"error", "code":..., "message":...}`.

### Authentication flow

Register:

```json
{"type":"auth.register","payload":{"username":"alice","password":"supersecret"}}
```

Login:

```json
{"type":"auth.login","payload":{"username":"alice","password":"supersecret"}}
```

The login response returns a session `token`.
For protected calls on a new socket, include token either at top level or in payload.

Resume session:

```json
{"type":"auth.resume","payload":{"token":"..."}}
```

### World calls

World meta:

```json
{"type":"world.meta"}
```

User state (protected):

```json
{"type":"world.state","token":"..."}
```

World region snapshot:

```json
{"type":"world.region","payload":{"min_x":0,"min_y":0,"max_x":20,"max_y":20}}
```

World patches since version:

```json
{"type":"world.patch_since","payload":{"from_version":0}}
```

### Actions

Claim neutral tile (protected):

```json
{"type":"action.claim","token":"...","payload":{"x":10,"y":3}}
```

Attack enemy tile (protected):

```json
{"type":"action.attack","token":"...","payload":{"x":11,"y":3}}
```

Place building on owned tile (protected):

```json
{"type":"action.build","token":"...","payload":{"x":10,"y":3,"building_type":"camp"}}
```

## Terminal testing

```bash
python3 scripts/packet_cli.py --host 127.0.0.1 --port 12345
```

Then paste JSON requests one-per-line.
`packet_cli` auto-fills `request_id` and `protocol_version` if omitted.

## In scope now

- Account registration/login and expiring sessions.
- Authoritative land ownership state in SQLite.
- Power resource regeneration and spend checks.
- Neutral claim, enemy attack-capture, and simple building placement.
- World versioning and patch event feed for incremental sync.

## Still out of scope

- Co-op/factions, diplomacy, advanced building progression.
- TLS transport and production deployment hardening.
