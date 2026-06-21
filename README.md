# bbc-sim — SBCO BACnet B-BC Simulator / Gateway

[![CI](https://github.com/takashikasuya/bacnet-sim-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/takashikasuya/bacnet-sim-gateway/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

> **Status: `v0.1.0-alpha` — experimental.** For development, CI, and integration
> testing only. **Not a production BACnet controller; not BTL-certified.** APIs,
> config schema, and CLI may change during the `0.x` series. Runs and is tested on
> **Python 3.12** (Ubuntu CI; Raspberry Pi ARM/ARM64 first-class).

実設備がなくても、**SBCO 標準ポイントリスト 1 つ**から標準準拠の仮想 BACnet B-BC を生成し、
**BACnet/IP（北向き）** で公開する統合シミュレータ兼プロトコル変換ゲートウェイです。
Raspberry Pi（ARM/ARM64）でのネイティブ実行を第一級でサポートします（Docker は任意）。

**想定ユーザー:** Building OS 開発者 / BACnet ゲートウェイ開発者 / BEMS・BAS の結合試験・検証担当者。
実設備なしで BACnet/IP の北向き挙動を再現し、上位システムの結合試験を回したい人に向けたツールです。

```
SBCO point list (CSV) ──▶ YAML (intermediate model) ──▶ Virtual B-BC
                                                          ├─ Northbound: BACnet/IP (UDP 47808)
                                                          └─ Southbound: MQTT / ZeroMQ (gateway mode)
```

- **Simulator モード** — 値を内部生成して仮想 B-BC を BACnet/IP に公開（上位システムの結合試験用）
- **Gateway モード** — 南向きの実データを BACnet オブジェクト化して北向きへ公開（実装済み: **MQTT / ZeroMQ**、CI 用 `memory://`。WoT / gRPC は設計上の対象でロードマップ）
- **Admin UI** — 状態確認・値/状態変更・点リスト再読込・ログ・バインディング確認をブラウザから（EP-007）

---

## 目次

- [アーキテクチャ（最重要の不変条件）](#アーキテクチャ最重要の不変条件)
- [前提環境](#前提環境)
- [Quickstart](#quickstart)
- [動作モード](#動作モード)
- [CLI リファレンス](#cli-リファレンス)
- [Admin UI](#admin-ui)
- [標準成果物のエクスポート](#標準成果物のエクスポート)
- [Docker（任意）](#docker任意)
- [開発](#開発)
- [リポジトリ構成](#リポジトリ構成)
- [ドキュメント](#ドキュメント)
- [手動受入確認](#手動受入確認)
- [ライセンス](#ライセンス)

---

## アーキテクチャ（最重要の不変条件）

```
            [ Building OS ]
                  ▲   (接続GW内部: AMQP/Kafka 等)
   [ Eclipse Hono / BACnet コネクタ ]      ← 上位接続ゲートウェイ（本製品の外）
                  ▲   BACnet/IP            ← NORTHBOUND（常に BACnet/IP）
   ┌──────────────────────────────────────────────┐
   │   bbc-sim  (Simulator / Gateway, 1 instance)  │
   └──────────────────────────────────────────────┘
                  ▼   MQTT / ZeroMQ (実装済) ・ WoT / gRPC (ロードマップ)   ← SOUTHBOUND
       [ フィールド側データ源 / センサ / 上流デバイス ]
```

設計を読み解く上で必ず押さえる不変条件（詳細は [`AGENTS.md`](AGENTS.md) / [`docs/adr`](docs/adr)）:

| 不変条件 | 意味 | 根拠 |
|----------|------|------|
| **北向き = BACnet/IP、南向き = バインディング** | 南向きは MQTT/ZeroMQ/WoT/gRPC（設計語彙）。MQTT は B-BC の北向き出力ではない。**実装済みは MQTT/ZeroMQ + `memory://`、WoT/gRPC はロードマップ** | ADR-005 |
| **`gateway_id` ≠ `bbc_id`** | 上位ゲートウェイ識別子を B-BC id に流用しない | ADR-003 |
| **1 インスタンス = 1 B-BC** | コンテナでもネイティブでも同じ単位 | ADR-002 |
| **SBCO 点リストが唯一の入力、YAML が共有中間モデル** | 全モードが同じ中間表現を共有 | ADR-001 / ADR-004 |
| **single-loop asyncio・非ブロッキング** | Core Object Model はイベントループ閉じ込め | ADR-010 |

代表的な通信フロー（Simulator / Gateway 取込・コマンド / 点リスト再読込 / Admin UI / BOWS）の
シーケンス図は [`docs/specs/communication-sequences.md`](docs/specs/communication-sequences.md) を参照。

---

## 前提環境

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)**（パッケージ/環境管理）
- Docker は任意（[Docker セクション](#docker任意)参照）

---

## Quickstart

```bash
# 1. 依存関係を同期（dev ツール込み）
uv sync

# 2. SBCO ポイントリスト CSV から simulator.yaml を生成
uv run bbc-sim generate-yaml \
  --input tests/fixtures/sample_pointlist.csv \
  --output config/simulator.yaml

# 3. 仮想 B-BC を起動（BACnet/IP 北向き公開）
uv run bbc-sim run --config config/simulator.yaml
```

> リポジトリにはすぐ試せる `config/simulator.yaml` が同梱されています。
> 自分の SBCO CSV を使う場合は手順 2 の `--input` を差し替えてください。

別ターミナルからクライアントで疎通確認:

```bash
uv run bbc-sim whois
uv run bbc-sim list-objects
```

---

## 動作モード

`--mode` で切り替えます（`simulator.yaml` の `mode` を上書き）。

| モード | BACnet 値の出所 | 南向き | 用途 |
|--------|-----------------|--------|------|
| `simulator` | 内部生成（random walk / sin / replay / scenario） | なし | 上位システム単体テスト |
| `gateway` | 南向きから受信した実データ | 通常必要（`--transport`） | プロトコル変換ハブ |
| `combined` | 内部生成＋南向きの混在 | 一部 | 段階的移行・混在試験 |

> `gateway`/`combined` でバインド対象があるのに `--transport` を省略すると、起動は継続しつつ
> 警告を出して南向きバインディングを無効化します（北向き BACnet/IP は提供されます）。
> ブローカ無しで試すには `--transport memory://`（プロセス内フェイク）を使えます。

Gateway モードの例（南向き MQTT を取り込み、BACnet/IP へ公開）:

```bash
uv run bbc-sim run -c config/simulator.yaml \
  --mode gateway \
  --transport mqtt://localhost:1883

# ブローカ無しの自己完結な動作確認（プロセス内フェイク）
uv run bbc-sim run -c config/simulator.yaml --mode gateway --transport memory://
```

---

## CLI リファレンス

すべて `uv run bbc-sim <command>`。`--help` で各コマンドの詳細を表示します。

### 生成・検証

| command | 用途 |
|---------|------|
| `generate-yaml -i <csv> -o <yaml>` | SBCO CSV → `simulator.yaml`（集約モード, ADR-011） |
| `validate -c <yaml>` | `simulator.yaml` を検証 |
| `validate-point-list -i <csv>` | SBCO CSV を検証 |

### ランタイム

| command | 主なオプション | 用途 |
|---------|---------------|------|
| `run -c <yaml>` | `--mode` / `--transport` / `--rest-port` / `--ui` | 仮想 B-BC を起動（BACnet/IP 北向き） |

`run` の主なフラグ:

- `--mode {simulator,gateway,combined}` — 動作モードの上書き
- `--transport <uri>` — 南向きトランスポート（`mqtt://host:port`, `zmq://<sub>|<pub>`, `memory://`）
- `--rest-port <port>` — REST 制御プレーンを公開（localhost 限定）
- `--ui / --no-ui` — Admin Web UI を `/ui` で公開（`--rest-port` 必須）

### クライアント（疎通確認）

| command | 用途 |
|---------|------|
| `whois` | デバイス探索（Who-Is/I-Am） |
| `list-objects` | object-list 列挙 |
| `read-property` / `read-property-multiple` | プロパティ読取 |
| `write-property` | プロパティ書込 |

### エクスポート

| command | 用途 |
|---------|------|
| `export -f <format> -c <yaml>` | 標準成果物の出力（[詳細](#標準成果物のエクスポート)） |

### BOWS コネクタ（BACnet → Building OS, EP-008）

仮想 B-BC を BACnet で読み取り、テレメトリを Building OS（[`gutp-building-os-oss`](#関連プロジェクト)）の
BACnet ネイティブスキーマ `bacnet-device-message` で MQTT へ供給します（下流の独立コネクタ, ADR-014）。

```bash
# 上り（テレメトリ）: 仮想 B-BC を読み、telemetry/{tenant}/{deviceId} へ publish
uv run bbc-sim bows run -t 127.0.0.1:47808 -d bbc-local-001 --tenant default \
  --transport mqtt://127.0.0.1:1883 --interval 10

# 下り（制御）: Building OS GatewayEgress(gRPC) を購読し ControlCommand を WriteProperty 実行
uv sync --extra grpc          # gRPC は optional-extra（基本/ARM は非依存, ADR-017）
uv run bbc-sim bows egress --endpoint buildingos:443 -g gw-001 -t 127.0.0.1:47808
```

```bash
# Hono northbound へ AMQP 1.0 で送る場合（optional extra が必要）
uv sync --extra amqp
uv run bbc-sim bows run -t 127.0.0.1:47808 -d bbc-local-001 \
  --transport amqps://hono.example:5671
# 認証情報は環境変数 BOWS_AMQP_USER / BOWS_AMQP_PASSWORD から注入（既定値なし）
```

`docs/specs/northbound-bows-buildingos.md`。AMQP/Hono は optional（[ADR-016](docs/adr/ADR-016-bows-amqp-and-downlink-control.md)）。
下り制御は Building OS の gRPC GatewayEgress を購読する双方向 stream クライアント
（[ADR-017](docs/adr/ADR-017-bows-grpc-downlink-control.md), #67）。mTLS 証明書は環境変数
`BOWS_EGRESS_TLS_CA/CERT/KEY` から注入（既定なし）。

---

## Admin UI

運用者向けの軽量 Web UI（FastAPI + Jinja2、ビルド工程なし）。REST 制御プレーンと同一プロセス・
同一ポートで動きます。北向きは BACnet/IP の**稼働状態の内省のみ**（上流へはプローブしません, ADR-005）。

```bash
uv run bbc-sim run -c config/simulator.yaml --rest-port 8080 --ui
# → http://127.0.0.1:8080/ui/
```

| 画面 | 内容 |
|------|------|
| Dashboard | モード・bind 状態・オブジェクト数・ヘルス（自動更新） |
| デバイス/オブジェクト | オブジェクト一覧、値の書込・Fault 注入・OOS トグル |
| バインディング | 南向き接続状態・最終受信・品質（gateway/combined） |
| 接続状態 | 北向き BACnet/IP カウンタ・bind/BBMD/FD 状態 |
| ログ | プロセス内リングバッファ（レベルフィルタ・自動更新） |
| 点リスト | `simulator.yaml` 再読込（検証 → 差分 → ライブ適用 or 再起動要求） |
| ヘルプ | 初回ガイドツアー・用語/概念・各画面の使い方 |

> **セキュリティ:** MVP は **`127.0.0.1`（localhost のみ）にバインド・認証なし**。同一ホストからの
> アクセスを前提とします。LAN/外部からのアクセスや認証は未対応（将来 EPIC）。LAN に公開する場合は
> 別途リバースプロキシ等で保護してください。信頼できないネットワークに直接晒さないこと。

---

## 標準成果物のエクスポート

```bash
uv run bbc-sim export -f ede    -c config/simulator.yaml -o out.csv   # EDE CSV
uv run bbc-sim export -f ieiej  -c config/simulator.yaml              # IEIEJ 風 CSV
uv run bbc-sim export -f pics   -c config/simulator.yaml              # PICS / BIBBs
uv run bbc-sim export -f jsonld -c config/simulator.yaml              # Brick/REC JSON-LD
uv run bbc-sim export -f wot    -c config/simulator.yaml              # WoT Thing Description
```

**未実装（ロードマップ）:** BACnet/SC（PR-F-071）、将来オブジェクト Schedule/TrendLog/
NotificationClass/Calendar/Accumulator（PR-F-070）、WoT *南向き*バインディング（PR-F-086）、
QUDT/full-REC エクスポート、BTL 認証支援、BOWS コネクタ（BACnet→Building OS, EP-008）。
詳細は [`docs/backlog/epic`](docs/backlog/epic)。

---

## Docker（任意）

ネイティブ実行が第一級ですが（ADR-008）、配布手段として Docker も提供します。
BACnet/IP のため `network_mode: host` を使います。

```bash
# 単体起動
docker compose -f docker/docker-compose.yml up --build

# 統合試験環境（B-BC gateway + Mosquitto）
docker compose -f docker/docker-compose.integration.yml up --build
```

> **BACnet/IP × Docker の注意:** BACnet/IP は **UDP 47808** とブロードキャストを使うため
> `network_mode: host` が必要です。host ネットワークは **Linux のみ**有効で、**macOS / Windows**
> の Docker Desktop はホストの UDP ブロードキャストを透過しないため Who-Is/I-Am が届きません
> （これらの OS ではネイティブ実行を推奨）。ホスト側で 47808 を他の BACnet アプリが
> 占有していないか確認してください。詳細は [`docs/troubleshooting.md`](docs/troubleshooting.md)。

---

## 関連プロジェクト

- **`gutp-building-os-oss`** — 本 B-BC を BACnet で読み取り上位に取り込む Building OS 側の
  関連 OSS（**別リポジトリとして公開**）。本リポジトリの docs・ADR が参照する `#159` / `#163`
  などの issue 番号は、その関連リポジトリ側のものです。

---

## 開発

```bash
uv sync                          # dev ツール込みで同期（default-groups=["dev"]）

uv run pytest                    # unit + loopback 統合（integration マーカーは除外）
uv run pytest -m integration     # 実サービス必要（docker/compose）

uv run ruff check                # lint
uv run mypy                      # 型チェック
```

開発フロー・コーディング規約・スコープ管理は [`AGENTS.md`](AGENTS.md) と
[`docs/development-workflow.md`](docs/development-workflow.md) を参照してください。

---

## リポジトリ構成

```
src/bbc_sim/
  cli.py                 # ルート Typer アプリ（サブコマンドを集約）
  models.py              # SimulatorConfig などのデータモデル
  yaml_generator/        # SBCO CSV → YAML 中間モデル（生成・検証）
  bacnet_objects/        # YAML → bacpypes3 BACnet オブジェクト構築
  simulator_runtime/     # ランタイム（app/runtime/cli）— BACnet/IP サーバ
  simulation/            # 値生成エンジン・ジェネレータ・フォールト注入
  southbound/            # 南向きバインディング（transport 抽象 + MQTT/ZeroMQ）
  services/              # BACnet クライアント（whois/read/write）
  rest/                  # REST 制御プレーン（status/reload/api）
  web/                   # Admin UI（Jinja2 テンプレート + ルータ）
  observability/         # ログリングバッファ
  export/                # 標準成果物エクスポート（EDE/PICS/JSON-LD/WoT）
  semantic/              # Brick セマンティックタグ導出
config/                  # simulator.yaml（サンプル同梱）
docker/                  # Dockerfile + compose（単体 / 統合）
docs/                    # 設計ドキュメント（下記参照）
tests/                   # pytest（fixtures に SBCO サンプル CSV）
```

---

## ドキュメント

レイヤ構成。**層を混在させない**のがルールです（読む順）:

```
Vision → Memory → ADR → Backlog → Spec
```

| 層 | パス | 答える問い |
|----|------|-----------|
| Vision | [`docs/vision`](docs/vision) | なぜ作るか |
| Memory | [`docs/memory`](docs/memory) | 知っておくべきこと（architecture/decisions/pitfalls） |
| ADR | [`docs/adr`](docs/adr) | なぜその設計か（**設計判断の正**） |
| Backlog | [`docs/backlog`](docs/backlog) | 何を作るか（PRD・EPIC） |
| Spec | [`docs/specs`](docs/specs) | どう振る舞うか |

通信フローのシーケンス図: [`docs/specs/communication-sequences.md`](docs/specs/communication-sequences.md)。

初見ユーザー向け: [ロードマップ](docs/roadmap.md) ・ [トラブルシューティング](docs/troubleshooting.md) ・
[セキュリティ運用ノート](docs/security-notes.md)。貢献するには [`CONTRIBUTING.md`](CONTRIBUTING.md)、
脆弱性報告は [`SECURITY.md`](SECURITY.md)。

エージェント運用の契約は [`AGENTS.md`](AGENTS.md)（最初に読む）と [`CLAUDE.md`](CLAUDE.md)。

---

## 手動受入確認

自動テストで担保できない項目（実機・実外部システムが必要）:

- **Raspberry Pi (ARM/ARM64) ネイティブ起動** — 実機で `uv sync && uv run bbc-sim run -c config/simulator.yaml`（PR-NF-019/020, ADR-008）。CI/loopback はネイティブ起動経路を `bbc-sim run` のサブプロセス e2e で確認済み、ARM 実機確認は手動。
- **YABE 北向き接続** — 同一サブネットの YABE から仮想 B-BC を探索し ReadProperty/WriteProperty を GUI 確認（TS-02..05）。プロトコル往復はループバック統合テストで確認済み。
- **Eclipse Hono / BACnet コネクタ取り込み (AC-7, TS-06..08)** — 北向き BACnet を接続ゲートウェイが取り込めること。CI/loopback では「BACnet クライアントが全オブジェクトを探索・読取できる」ことで確認済み（`test_upper_integration.py`）、実 Hono 連携は手動。
- **Ditto / Building OS まで疎通 (AC-7, AC-8, TS-07..08)** — 実 Ditto・Building OS への到達は手動。
- **異サブネット探索 (AC-10, TS-10)** — `network.foreign_bbmd`（Foreign Device 登録）・`network.bbmd_bdt`（BBMD 動作）を実装・ユニットテスト済み。実 BBMD を挟んだ探索は手動。

---

## ライセンス

[Apache License 2.0](LICENSE)。
