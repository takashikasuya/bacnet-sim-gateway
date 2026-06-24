# Security notes (deployment)

> Consolidated operational-security guidance. For reporting vulnerabilities, see
> [`../SECURITY.md`](../SECURITY.md). Most real-world risk here is
> **misconfiguration**, not code.

`bbc-sim` is experimental software for development, CI, and integration testing.
Run it only on networks you control.

## BACnet/IP (northbound)

- BACnet/IP uses **UDP/47808** with **no authentication or encryption** — this is
  inherent to the protocol, not a bug.
- Keep it on a **trusted, segmented building/test network**. Never route it to the
  public internet.
- BBMD / Foreign Device Registration widens reachability across subnets — only
  enable it where you trust every participant.

## Admin UI

- Binds to **`127.0.0.1` only, with no authentication** (MVP).
- Do not expose it to untrusted networks. If you need remote access, put an
  authenticating reverse proxy in front of it.

## Southbound transports (gateway mode)

- **MQTT / ZeroMQ**: use broker-side ACLs and TLS in any shared environment. The
  bundled Mosquitto config (`docker/mosquitto.conf`) is **anonymous** and meant
  for local testing only.

## BOWS connector credentials

- AMQP password and gRPC **mTLS** material are injected via environment variables
  (`BOWS_AMQP_PASSWORD`, `BOWS_EGRESS_TLS_CA` / `BOWS_EGRESS_TLS_CERT` /
  `BOWS_EGRESS_TLS_KEY`). There are **no defaults**.
- **Never commit** certificates, keys, or credentials. `.gitignore` blocks common
  patterns (`.env*`, `*.pem`, `*.key`, `*credentials*`) as a safety net, but treat
  that as a backstop, not a guarantee.

## Docker

- BACnet/IP requires `network_mode: host` (see README → Docker). Host networking
  removes container network isolation — only run it on hosts you trust.
