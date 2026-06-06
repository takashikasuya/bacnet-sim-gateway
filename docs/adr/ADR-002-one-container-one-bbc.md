# ADR-002: 1 Docker Container = 1 B-BC

- **Date:** 2026-06-06
- **Status:** Accepted
- **原典:** 要件定義書 §4, §13, §22-2 / PRD CON-2

## Context

1 コンテナに複数の B-BC を載せる構成も技術的には可能だが、BACnet/IP のポート（UDP 47808）・Device Identifier・ネットワーク境界が B-BC ごとに独立しているため、複数同居はアドレス衝突と障害切り分けの困難を生む。

## Decision

**1 Docker Container = 1 B-BC** を物理的対応として固定する。Gateway モード（南向きバインディング）でもこの単位を崩さない。複数 B-BC が必要なら複数コンテナを起動する。

## Consequences

- 各 B-BC が独立した BACnet/IP エンドポイントを持ち、障害注入・再起動の影響が他に波及しない。
- `network_mode: host` 推奨（BACnet/IP ブロードキャストのため）。複数コンテナ同一ホスト時はポート/サブネット設計が必要。
- スケールはコンテナ数で表現。
