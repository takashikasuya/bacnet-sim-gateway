# Security Policy

> 日本語の要約は本文の下部にあります。

## Project maturity

`bbc-sim` is **experimental, pre-1.0 software** (`v0.1.x-alpha`) intended for
**development, CI, and integration testing** — *not* a production BACnet
controller and *not* BTL-certified. Operate it only on networks you control.

## Supported versions

Only the latest `0.x` release line receives security fixes. There is no
long-term-support branch during the `0.x` series.

| Version | Supported |
|---------|-----------|
| latest `0.x` | ✅ |
| older `0.x`  | ❌ |

## Reporting a vulnerability

**Do not open a public issue for security problems.**

- Preferred: GitHub **Private vulnerability reporting** (repository → *Security* →
  *Report a vulnerability*), which opens a private advisory.
- Alternative: email the maintainer at **t.kasuya@gmail.com** with a clear
  description, affected version/commit, and reproduction steps.

We aim to acknowledge reports within **5 business days** and to agree on a
disclosure timeline with the reporter. Please allow a reasonable embargo before
public disclosure.

## Operational security notes (read before deploying)

This project speaks several network protocols; most real-world risk comes from
**misconfiguration**, not code:

- **BACnet/IP (northbound)** uses **UDP/47808** with **no authentication or
  encryption** (by protocol design). Expose it only on trusted, segmented
  building networks. Do not route it to the public internet.
- **Admin UI** binds to **`127.0.0.1` with no authentication** in MVP. Do not
  expose it to untrusted networks; place a reverse proxy with auth in front if
  remote access is required. (See README → *Admin UI*.)
- **Southbound transports (MQTT / ZeroMQ)** — use broker-side ACLs/TLS; the
  sample Mosquitto config is anonymous and for local testing only.
- **BOWS connector** — AMQP credentials and gRPC **mTLS** material are injected
  via environment variables (`BOWS_AMQP_PASSWORD`, `BOWS_EGRESS_TLS_CA/CERT/KEY`).
  Never commit certificates or credentials to the repository.

See [`docs/security-notes.md`](docs/security-notes.md) for the consolidated
deployment guidance.

---

## 日本語要約

`bbc-sim` は **実験的な 1.0 未満ソフトウェア**で、開発・CI・結合試験用です（本番制御・BTL 認証は対象外）。

- **脆弱性は公開 Issue にしないでください。** GitHub の *Private vulnerability reporting* か、
  **t.kasuya@gmail.com** へ非公開で連絡してください（影響バージョン/commit・再現手順を添えて）。
- サポート対象は最新の `0.x` のみ。
- 運用上の注意: BACnet/IP（UDP 47808・無認証）、Admin UI（127.0.0.1・無認証）、
  MQTT/ZeroMQ、BOWS の mTLS/認証情報は env 注入。詳細は
  [`docs/security-notes.md`](docs/security-notes.md)。
