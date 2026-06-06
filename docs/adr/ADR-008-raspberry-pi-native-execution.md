# ADR-008: Raspberry Pi / ネイティブ実行をファーストクラスとし、Docker は任意とする

- **Date:** 2026-06-07
- **Status:** Accepted
- **原典:** PRD v1.4 PR-NF-019, PR-NF-020, CON-2 / 要件定義書 §13

## Context

当初は配布手段として Docker / docker compose を前提にしていた（要件定義書 §13、PR-NF-005）。しかし実運用では **Raspberry Pi 上で Docker を使わずに動かしたい** という要求がある。Docker は BACnet/IP のブロードキャスト（Who-Is/I-Am）に `network_mode: host` を要する、ARM 環境でのイメージ事情、現場の制約など、必須にすると導入障壁になる。

## Decision

- **Raspberry Pi（ARM/ARM64, Linux）でのネイティブ実行をファーストクラス**の実行形態とする（PR-NF-019）。
- **Docker は配布・統合試験のための任意手段**とし、必須にしない（PR-NF-020）。ネイティブ実行は `uv` による依存解決 ＋ `bbc-sim` CLI で行う。
- 構成原則「1 = 1 B-BC」は **コンテナ単位ではなくランタイムインスタンス（プロセス）単位**に一般化する（CON-2 / [[ADR-002]] を更新）。さらに [[ADR-011]] で「1 instance = 1 Virtual B-BC（1..N BACnet Device を公開）」に精緻化。
- BACnet/IP のブロードキャストはネイティブ実行ではホスト NIC 上で直接動作し、Docker のネットワーク制約を受けない。

## Consequences

- 実装は Docker 固有機能に依存してはならない（設定・パス・ネットワークはネイティブでも成立すること）。
- CI / 複数 B-BC 同居など Docker が有利な場面では引き続き Compose を使う（`compose-integration-env.md`）。
- ARM 上でビルド可能な BACnet ライブラリ・依存であること（ライブラリ選定の判断材料。decisions.md）。
- ❓ サポート OS/アーキ・Python 配布形態（uv / システム Python / 単一バイナリ）は未確定（要件 §13.1）。
- 関連: [[ADR-002]]（1 instance = 1 B-BC）。
