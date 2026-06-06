# ADR-002: 1 Docker Container = 1 B-BC

- **Date:** 2026-06-06
- **Status:** Accepted
- **原典:** 要件定義書 §4, §13, §22-2 / PRD CON-2

## Context

1 コンテナに複数の B-BC を載せる構成も技術的には可能だが、BACnet/IP のポート（UDP 47808）・Device Identifier・ネットワーク境界が B-BC ごとに独立しているため、複数同居はアドレス衝突と障害切り分けの困難を生む。

## Decision

**1 ランタイムインスタンス = 1 B-BC** を固定する。インスタンスは Docker コンテナでもネイティブプロセスでもよい（ネイティブ実行は [[ADR-008]]）。Gateway モード（南向きバインディング）でもこの単位を崩さない。複数 B-BC が必要なら複数インスタンスを起動する。

> v0.1 当初は「1 Docker Container = 1 B-BC」と表現していたが、Raspberry Pi ネイティブ実行（[[ADR-008]]）に合わせ「ランタイムインスタンス」に一般化（PRD v1.4 CON-2）。

## Consequences

- 各 B-BC が独立した BACnet/IP エンドポイントを持ち、障害注入・再起動の影響が他に波及しない。
- BACnet/IP ブロードキャストのため、Docker では `network_mode: host` 推奨。ネイティブ実行ではホスト NIC で直接動作。
- 同一ホストに複数インスタンスを置く場合はポート/サブネット設計が必要。
- スケールはインスタンス数で表現。
