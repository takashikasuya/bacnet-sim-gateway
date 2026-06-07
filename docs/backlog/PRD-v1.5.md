# SBCO BACnet B-BC Simulator / Gateway 製品要求仕様書 (PRD)

| 項目 | 内容 |
|------|------|
| 文書名 | SBCO BACnet B-BC Simulator / Gateway 製品要求仕様書 (Product Requirements Specification) |
| バージョン | v1.5 (Draft) |
| 上位/関連文書 | SBCO BACnet B-BC Simulator 要件定義書 v1.1 (`../specs/requirements-definition-v1.1.md`) |
| 位置づけ | 要件定義書の上位文書。「何を・なぜ・誰のために・どこまで満たせば完成か」を定義する |
| 対象読者 | プロダクトオーナー、システムエンジニア、開発者、品質保証、連携製品開発者 |

> 本書は製品レベルの**要求 (Requirements)** を扱う。実装方式・データ構造・CLI仕様などの**設計 (Specification)** は要件定義書 v1.1 を正とし、本書からトレースする。

### 変更履歴

| 版 | 主な変更点 |
|----|-----------|
| v1.0 | 要件定義書 v1.1 を上位化した初版 |
| v1.1 | 上位連携の前提（Eclipse Hono 等のゲートウェイ経由で Building OS へ）を明文化。シミュレータ／ゲートウェイのデュアルモードと多プロトコルバインディングを追加 |
| v1.2 | **バインディングの方向性を修正**。ノースバウンド＝BACnet/IP（上位接続ゲートウェイが取り込む）、サウスバウンド＝MQTT / ZeroMQ / Web of Things / gRPC のバインディングに再定義。ゲートウェイモードを「南向きプロトコルのデータ源を BACnet オブジェクト化して北向きへ公開する」構成として明確化 |
| v1.3 | 各 BACnet オブジェクトに**セマンティックタグ（`tags` プロパティ）**を付与する要求を追加。SBCO `tags` 列から決定的に生成し、語彙は **BACnet 標準タグ ＋ Project Haystack** を既定（将来 ASHRAE 223P へ連携） |
| v1.4 | **Raspberry Pi（ARM）でのネイティブ実行**を要求化（PR-NF-019/020）。Docker は配布手段の一つであり必須ではない。SBCO 原典リポジトリの URL を明記 |
| v1.5 | 設計 grill (2026-06-07) の確定を反映: **device-mapping mode**（aggregated/multi-device/auto-partition, PR-F-091〜094, CON-8）、**BACnet タグの Brick 由来生成**（PR-F-017 改, AC-14 改）、**南向きアドレス local_id 第一**（PR-F-090 改）。SBCO 原典の事実補正（labels/scale/`&&`/point_type 意味論）。決定: ADR-009〜012、ADR-002/006/007/008 改訂 |
| v1.6 | **管理者向け Web UI** を追加（EP-007 / MVP-2）。PR-F-053〜057 を新設し PR-F-052 を「任意」から正式要求（S）へ格上げ。北向きは BACnet/IP 稼働状態の内省のみ（ADR-005 厳守、上流プローブなし）、軽量サーバレンダリング（Jinja2 + 素の JS fetch・jinja2 のみ追加・Pi ネイティブ）、初回利用者向けオンボーディングを必須化。AC-15/16 追加。MVP は localhost/LAN・認証なし（認証/外部公開は将来 EPIC） |

---

## 1. はじめに

### 1.1 目的

スマートビルディング連携基盤（BACnet 接続ゲートウェイ → Building OS）の開発・結合試験では、実設備の BACnet コントローラ（B-BC）が必要になる。しかし実設備は、

- 開発初期には存在しない、または調達コストが高い
- 試験のたびに物理アクセスが必要で、CI/CD に組み込めない
- 異常系（通信断・異常値・OutOfService）を意図的に再現しにくい

本製品は、**SBCO 標準ポイントリストを唯一の入力として仮想 B-BC を生成し、値を内部生成して BACnet/IP に公開する（シミュレータモード）**とともに、**各 BACnet オブジェクトをサウスバウンドのプロトコル（MQTT / ZeroMQ / Web of Things / gRPC）にバインドし、南向きのデータ源を BACnet オブジェクトとして北向きへ公開する（ゲートウェイモード）**ことで、実設備の代替かつプロトコル変換ハブとして、BACnet を起点とする結合試験を完結させる。

### 1.2 連携方向の前提 (North/Southbound Assumption)

- **ノースバウンド（上位インタフェース）＝ BACnet/IP。** 上位系（Building OS）は、Eclipse Hono 等の接続ゲートウェイ（BACnet コネクタを含む）経由でこの BACnet を取り込む前提とする。本製品は上位系へ直結せず、常に BACnet/IP を北向きに提供する。
- **サウスバウンド（下位インタフェース）＝ MQTT / ZeroMQ / Web of Things / gRPC のバインディング。** ゲートウェイモードでは、これら南向きプロトコルが各 BACnet オブジェクトの値の主たる出所（source of record）となる。
- シミュレータモードでは南向きバインディングを用いず、値を内部生成する。

### 1.3 背景・前提課題 (Problem Statement)

| # | 課題 | 影響 |
|---|------|------|
| P-1 | 実 B-BC がないと上流（接続ゲートウェイ/Building OS）の結合試験が始められない | 開発の直列化・遅延 |
| P-2 | 実設備では異常系の再現が困難 | フォールトトレランス検証不足 |
| P-3 | 試験が手作業で再現性が低く、CI に乗らない | 回帰検証コスト増 |
| P-4 | ポイント定義（SBCO）と BACnet モデルの整合を人手で取っている | マッピング誤り・属人化 |
| P-5 | 南向きの多様なプロトコル（MQTT/ZeroMQ/WoT/gRPC）を BACnet 化する処理が連携先ごとに個別実装される | 重複開発・整合性低下 |

### 1.4 用語

主要用語は「付録A 用語集」を参照。最重要原則として **`gateway_id` と `bbc_id` は別概念であり混同してはならない**（要件定義書 4章・22章）。

---

## 2. 製品ビジョンとゴール

### 2.1 ビジョン

> 実設備がなくても、SBCO 標準ポイントリスト 1 つから標準準拠の仮想 B-BC を BACnet/IP で北向きに公開し（シミュレータ）、さらに同じ BACnet オブジェクトを南向きの MQTT / ZeroMQ / Web of Things / gRPC データ源にバインドして、南向きの実データを BACnet 化して上位へ供給できる（ゲートウェイ）。上位系は Eclipse Hono 等の接続ゲートウェイ経由でこの BACnet を取り込み、Building OS まで繋がる。

### 2.2 製品ゴール (Product Goals)

| ID | ゴール | 成功の方向性 |
|----|--------|--------------|
| G-1 | SBCO ポイントリストを単一の入力ソースとした仮想 B-BC 生成 | 入力からの自動化・再現性 |
| G-2 | ANSI/ASHRAE 135 / ISO 16484-5 準拠の BACnet/IP 北向き公開 | 標準クライアント（YABE 等）との相互運用 |
| G-3 | 接続ゲートウェイ（Eclipse Hono 等）/ Ditto / Building OS との結合試験を第一目的として成立 | 連携経路のエンドツーエンド検証 |
| G-4 | 実設備なしで正常系・異常系の統合試験環境を提供 | フォールトインジェクション対応 |
| G-5 | CI/CD（Docker / GitHub Actions）へ組み込み可能 | 回帰試験の自動化 |
| G-6 | BACnet/SC・PICS・EDE 等への拡張余地を持つ設計 | 将来の規格適合・成果物出力 |
| G-7 | 各 BACnet オブジェクトを南向きの MQTT / ZeroMQ / WoT / gRPC にバインドするゲートウェイ機能 | 南向きデータ源の統一的な BACnet 化 |

### 2.3 非ゴール (Non-Goals)

- 実設備の制御ロジック（実際の空調制御アルゴリズム等）の忠実な再現は目的としない。あくまで**通信・データ・連携の試験**が対象。
- BTL 正式認証の取得そのものは本製品の責務外（適合**支援**までを将来対象とする）。
- SBCO ポイントリスト自体の作成・管理は範囲外（外部リポジトリを入力として扱う）。
- 本番運用グレードのゲートウェイ可用性（HA・大規模スケール・冗長化）は当面の主目的としない（試験・連携検証を主眼とし、堅牢化は将来検討）。

---

## 3. スコープ

### 3.1 スコープ内 (In Scope)

- SBCO 標準ポイントリスト（CSV/XLSX）の取り込みと検証
- YAML 中間モデルの生成・検証
- **シミュレータモード**: 仮想 B-BC ランタイム（1 コンテナ = 1 B-BC）、値の内部生成、BACnet/IP の北向き公開
- BACnet オブジェクト群と主要 BACnet サービス（北向き）
- シミュレーション（Random Walk / Sin / Replay / Scenario）とフォールトインジェクション
- **ゲートウェイモード**: 各 BACnet オブジェクトを南向き MQTT / ZeroMQ / Web of Things / gRPC へ双方向バインド（南向きが主）
- 上位連携前提: 北向き BACnet/IP を Eclipse Hono 等の接続ゲートウェイ／Ditto が取り込み Building OS へ
- REST API による情報取得・制御・シナリオ操作
- CLI ツール群
- **ネイティブ実行（Raspberry Pi / ARM、Docker 非依存）** ＋ Docker / Docker Compose による配布・統合試験環境

### 3.2 スコープ外 / 将来対象 (Out of Scope / Future)

| 区分 | 項目 |
|------|------|
| 将来対象 | BACnet/SC、Schedule、Trend Log、Calendar、Notification Class、Accumulator、Alarm/Event |
| 将来対象 | PICS / EDE / IEIEJ CSV 出力、BTL 適合支援 |
| 将来対象 | 意味モデル出力（REC, Brick, QUDT, WoT TD の意味付け, JSON-LD） |
| 範囲外 | SBCO ポイントリストの編集・マスタ管理 |
| 範囲外 | 実制御アルゴリズムの忠実再現 |
| 範囲外 | 上位接続ゲートウェイ（Hono 等）自体の実装、Building OS への直結 |
| 範囲外 | ゲートウェイの本番 HA・大規模運用（当面） |

---

## 4. アーキテクチャ（運用モードと連携方向）

本製品は単一イメージで 2 つのモードを持ち、**併用 (Combined) も可能**とする。両モードは同一の内部オブジェクトモデル（YAML 中間モデルに由来）を共有する。**北向きは常に BACnet/IP**、**南向きはバインディング（MQTT/ZeroMQ/WoT/gRPC）**。

```
                         [ Building OS ]
                               ▲   (接続GW内部: AMQP/Kafka 等で上位アプリへ)
              [ Eclipse Hono / BACnet コネクタ ]      ← 上位接続ゲートウェイ（前提・本製品の外）
                               ▲   BACnet/IP          ← NORTHBOUND（本製品の上位インタフェース）
   ┌───────────────────────────────────────────────────────────┐
   │        SBCO BACnet B-BC  Simulator / Gateway                │
   │   ┌──────────────────┐      ┌──────────────────────────┐   │
   │   │ Simulator Mode    │ 共有 │ Gateway Mode (Binding)    │   │
   │   │ 値を内部生成       │モデル│ BACnetオブジェクト ⇄       │   │
   │   │ (random walk 等)   │      │ 南向きプロトコル           │   │
   │   └──────────────────┘      └──────────────────────────┘   │
   └───────────────────────────────────────────────────────────┘
                               ▼   MQTT / ZeroMQ / Web of Things / gRPC   ← SOUTHBOUND（バインディング・主）
          [ フィールド側データ源 / センサ / 機器シミュレータ / 上流デバイス ]
```

### 4.1 モード定義

| モード | 役割 | BACnet 値の出所 | 北向き | 南向き |
|--------|------|-----------------|--------|--------|
| Simulator | SBCO から仮想 B-BC を生成し値を内部生成 | 内部生成（random walk/sin/replay/scenario） | BACnet/IP | なし |
| Gateway | 南向きプロトコルのデータ源を BACnet オブジェクト化 | 南向き（MQTT/ZeroMQ/WoT/gRPC） | BACnet/IP | バインディング（主） |
| Combined | 一部は内部生成、一部は南向きバインドを併用 | 内部生成＋南向きの混在 | BACnet/IP | バインディング（一部） |

### 4.2 バインディングの方向性（主：サウスバウンド）

- **Telemetry（取込）**: 南向き（MQTT/ZeroMQ/WoT/gRPC）で受信した値 → BACnet `presentValue` を更新 → 北向き `ReadProperty` で取得可能。
- **Command（送出）**: 北向き BACnet `WriteProperty`（Writable のみ、上位系から接続ゲートウェイ経由）→ 南向きプロトコルへコマンド送出。
- バインディングの主たる方向はサウスバウンド（値の source of record は南向きにある）。北向き BACnet はその投影。

### 4.3 構成原則

- 1 ランタイムインスタンス = 1 B-BC（Docker コンテナでもネイティブプロセスでも同様。要件定義書 4章 / ADR-008）。ゲートウェイモードもこの単位を崩さない。
- `gateway_id`（上位ゲートウェイ識別子）と `bbc_id` を混同しない。
- 上位系（Building OS）への接続は接続ゲートウェイ（Hono 等）を経由する前提とし、本製品は北向き BACnet/IP のみを提供する（上位系直結を前提としない）。

---

## 5. ステークホルダーとユーザーペルソナ

| ペルソナ | 役割 | 本製品への主要ニーズ |
|----------|------|----------------------|
| 接続ゲートウェイ開発者 | Hono/Ditto 等への BACnet 取り込み開発 | 安定した北向き BACnet/IP エンドポイント |
| Building OS / 連携基盤開発者 | 上位連携開発 | 実設備なしで Building OS まで通る試験経路 |
| 南向き機器/データ源開発者 | MQTT/ZeroMQ/WoT/gRPC のデバイス・サービス開発 | 南向きデータが BACnet 化されることの確認 |
| QA / 試験担当 | 結合・回帰試験 | 再現可能・自動化可能・異常系を注入できる環境 |
| BACnet 検証者 | 相互運用確認 | YABE 等の標準クライアントから探索・読み書きできること |
| ビル設計/データモデル担当 | SBCO ポイント定義 | 自分のポイントリストがそのまま試験対象になること |

---

## 6. 主要ユースケース

| UC | シナリオ | 概要 |
|----|----------|------|
| UC-1 | ポイントリスト→仮想設備 | SBCO CSV を入力し YAML 生成、仮想 B-BC を Docker 起動（Simulator） |
| UC-2 | BACnet 探索・読取 | YABE 等から Who-Is/I-Am で発見し ReadProperty で値取得（北向き） |
| UC-3 | 南向きデータの BACnet 化 | 南向き MQTT/ZeroMQ/WoT/gRPC のデータ源 → Gateway → 北向き BACnet オブジェクト（Telemetry） |
| UC-4 | 上位連携結合試験 | 北向き BACnet/IP → Eclipse Hono（BACnet コネクタ）→ Building OS |
| UC-5 | デジタルツイン連携 | 北向き BACnet/IP → 接続ゲートウェイ → Eclipse Ditto → Building OS |
| UC-6 | 制御ループ試験 | 上位（Building OS）→接続GW→北向き BACnet WriteProperty→Gateway→南向きコマンド送出（Command） |
| UC-7 | 多プロトコル同時取込 | Combined モードで内部生成オブジェクトと南向きバインドオブジェクトを同一 BACnet/IP に公開 |
| UC-8 | 異常系試験 | 通信断・異常値・値凍結・OutOfService を注入し上流挙動を確認 |
| UC-9 | CI 回帰試験 | GitHub Actions 上で Docker 起動→結合テスト自動実行 |
| UC-10 | サブネット越え探索 | BBMD / Foreign Device Registration を介した北向き発見 |

---

## 7. 製品要求

> 優先度は MoSCoW（**M**ust / **S**hould / **C**ould / **W**on't=将来）で示す。MVP 列は要件定義書 21章のフェーズ（1/2/3）に対応。「原典」は要件定義書 v1.1 の章番号（新規は「新」）。

### 7.1 機能要求 (Functional Requirements)

#### 入力・変換

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-001 | SBCO 標準ポイントリスト（CSV/XLSX）を入力として受け付ける | M | 1 | 5 |
| PR-F-002 | 必須列の存在・妥当性を検証し、欠落時はエラーとして報告する | M | 1 | 5,15 |
| PR-F-003 | `gateway_id` をゲートウェイ識別子として扱い、`bbc_id` に流用しない | M | 1 | 4,22 |
| PR-F-004 | 入力から YAML 中間モデルを生成する | M | 1 | 6 |
| PR-F-005 | データ型と writable から BACnet object type を自動推定する | M | 1 | 6 |
| PR-F-006 | BACnet 列（device_id_bacnet 等）が存在する場合は推定より優先する | M | 1 | 5 |
| PR-F-007 | 生成 YAML の妥当性検証を提供する | M | 1 | 15 |

object type 自動推定（PR-F-005）の規定：

| データ型 | writable | object type |
|----------|----------|-------------|
| float | ReadOnly | AnalogInput |
| float | Writable | AnalogValue |
| bool | ReadOnly | BinaryInput |
| bool | Writable | BinaryValue |
| enum | ReadOnly | MultiStateInput |
| enum | Writable | MultiStateValue |

#### 仮想 B-BC / BACnet 北向き公開（Simulator Mode）

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-010 | 1 コンテナ = 1 B-BC として仮想コントローラを生成する | M | 1 | 4,13 |
| PR-F-011 | `bbc_id` を設定ファイルまたは環境変数で与えられる | M | 1 | 4 |
| PR-F-012 | Device Object（必須プロパティ一式）を提供する | M | 1 | 7 |
| PR-F-013 | Analog/Binary/Multi-state の Input/Output/Value オブジェクトを提供する | M | 1 | 8 |
| PR-F-014 | 各オブジェクトの共通・型別必須プロパティを提供する | M | 1 | 10 |
| PR-F-015 | BACnet/IP ネットワークへ北向き公開する | M | 1 | 3,14 |

#### セマンティックタグ（北向き）

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-016 | 各 BACnet オブジェクトに `tags` プロパティ（name＋任意 value のタグ集合）を設け、ReadProperty/RPM で取得可能にする | S | 2 | 新 |
| PR-F-017 | BACnet セマンティックタグを **Brick クラス（device_type/point_type）から決定的に生成**する。SBCO `tags` 列はビル OS 検索タグとして metadata に保持（別概念。ADR-012） | S | 2 | 新 |
| PR-F-018 | タグ語彙は BACnet 標準タグ ＋ Project Haystack を既定とする（将来 ASHRAE 223P へ連携）。未知タグは検証で警告し独自タグとして保持する | S | 2 | 新 |

#### BACnet サービス（北向き）

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-020 | Who-Is / I-Am に応答する | M | 1 | 9 |
| PR-F-021 | ReadProperty を提供する | M | 1 | 9 |
| PR-F-022 | ReadPropertyMultiple を提供する | M | 1 | 9 |
| PR-F-023 | WriteProperty を提供し、Writable オブジェクトのみ変更可能とする | M | 1 | 9 |
| PR-F-024 | Dynamic Device/Object Binding を提供する | M | 1 | 9 |
| PR-F-025 | WritePropertyMultiple を提供する | S | 2 | 9 |
| PR-F-026 | Who-Has / I-Have に応答する | S | 2 | 9 |
| PR-F-027 | DeviceCommunicationControl / ReinitializeDevice / TimeSynchronization を提供する | S | 2 | 9 |
| PR-F-028 | SubscribeCOV / Confirmed・UnconfirmedCOVNotification を提供する | S | 2 | 9 |

#### シミュレーション・異常系

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-030 | Random Walk / Sinusoidal / Replay / Scenario の値生成モードを提供する | S | 2 | 11 |
| PR-F-031 | フォールトインジェクション（通信断・値凍結・異常値・OutOfService・Fault 状態）を提供する | S | 2 | 11 |

#### ネットワーク（サブネット越え・北向き）

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-040 | 同一サブネットで Who-Is/I-Am 探索を可能にする | M | 1 | 12 |
| PR-F-041 | BBMD / Foreign Device Registration で異サブネット探索に対応する | S | 2 | 12 |

#### 運用モードとサウスバウンド・バインディング（Gateway Mode）

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-080 | 起動時に動作モード（simulator / gateway / combined）を設定で選択できる | M | 2 | 新 |
| PR-F-081 | Simulator モードと Gateway モードは同一の内部オブジェクトモデルを共有する | M | 2 | 新 |
| PR-F-082 | Gateway モードで各 BACnet オブジェクトを**南向き**プロトコルにバインドする | M | 2 | 新 |
| PR-F-083 | バインディングは双方向とする：Telemetry は南向き→BACnet（北向き読取）、Command は北向き WriteProperty→南向き送出。主たる方向はサウスバウンド | M | 2 | 新 |
| PR-F-084 | MQTT 南向きバインディングを提供する（Telemetry トピックを subscribe して取込、Command トピックへ publish） | M | 2 | 18,新 |
| PR-F-085 | ZeroMQ 南向きバインディングを提供する | S | 2 | 新 |
| PR-F-086 | Web of Things 南向きバインディングを提供する（Thing の Property/Action/Event を Consumer として取込・起動し BACnet に対応付け） | S | 3 | 新 |
| PR-F-087 | gRPC 南向きバインディングを提供する（read / write / streaming） | S | 2 | 新 |
| PR-F-088 | 北向き BACnet/IP を上位接続ゲートウェイ（Eclipse Hono 等）が取り込める形で提供する | M | 2 | 新 |
| PR-F-089 | 上位経路上の Eclipse Ditto（デジタルツイン）連携を阻害しない（北向き BACnet 経由） | S | 2 | 19,新 |
| PR-F-090 | 南向きアドレス（topic/endpoint/service）は **`local_id` を第一源**とし、明示 binding 設定 > `local_id` > building/device/point 導出 の順で決定する | S | 2 | 18,新 |

> 南向き MQTT のトピック規則は要件定義書 18章を踏襲（`building/{building}/device/{device}/point/{point}/telemetry` を取込、`.../command` へ送出）。他プロトコルは同等の階層命名規則を適用する。

#### 設備マッピング（Device Mapping — runtime mode と直交）

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-091 | device-mapping mode（aggregated / multi-device）を選択できる。runtime mode と直交 | M | 1/2 | 新 |
| PR-F-092 | aggregated: 点リスト全体を 1 BACnet Device に集約（跨設備で instance を再採番） | M | 1 | 新 |
| PR-F-093 | multi-device: SBCO device ごとに BACnet Device を生成（実設備忠実、instance_no_bacnet 尊重） | S | 2 | 新 |
| PR-F-094 | auto-partition: object 数 > `limits.max_objects_per_device`（既定 1000）で Virtual Device に自動分割 | C | 3 | 新 |

> 詳細は `../specs/device-mapping.md`・[[ADR-011]]。ペルソナ指針: Building OS 開発者→aggregated、Gateway 開発者→multi-device。

#### 外部 API / UI

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-050 | REST API で device/object 情報取得・値書込・シナリオ変更を提供する | S | 2 | 17 |
| PR-F-052 | 管理者向け Web UI を提供する（状態確認・値/状態変更・ログ・バインディング・点リスト再読込・オンボーディング） | S | 2 | 3 |
| PR-F-053 | REST/UI でログ（検証/バインディング/Fault/BACnet サービス）を閲覧できる | S | 2 | 新 |
| PR-F-054 | REST/UI で runtime 状態（mode・北向き bind/カウンタ・南向き接続）を取得できる | S | 2 | 新 |
| PR-F-055 | REST/UI で南向きバインディング状態（protocol/address/最終更新/品質）を確認できる | S | 2 | 新 |
| PR-F-056 | REST/UI で点リスト再読込（検証→差分→適用 or 再起動要求）を実行できる | S | 2 | 新 |
| PR-F-057 | 初回利用者向けオンボーディング（ガイド付きツアー・常設 Help・コンテキストヘルプ・空状態ガイド）を提供する | S | 2 | 新 |

#### CLI

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-060 | generate-yaml / validate / run の基本 CLI を提供する | M | 1 | 15 |
| PR-F-061 | whois / read-property / read-property-multiple / write-property / list-objects を提供する | M | 1 | 15 |
| PR-F-062 | validate-point-list を提供する | M | 1 | 15 |
| PR-F-063 | 起動 CLI でモードと有効な南向きバインディングを指定できる | S | 2 | 新 |

#### 将来機能

| ID | 要求 | 優先度 | MVP | 原典 |
|----|------|:---:|:---:|:---:|
| PR-F-070 | Schedule / Trend Log / Notification Class / Calendar / Accumulator を提供する | W | 3 | 8,19 |
| PR-F-071 | BACnet/SC に対応する | W | 3 | 19 |
| PR-F-072 | PICS / EDE / IEIEJ CSV を出力する | W | 3 | 19 |
| PR-F-073 | 意味モデル（REC/Brick/QUDT/WoT TD 意味付け/JSON-LD）出力に対応する | W | 3 | 19 |

> 意味付けの近接実装は PR-F-016〜018（BACnet ネイティブ `tags`、語彙＝標準タグ＋Haystack、MVP-2）で担い、PR-F-073 の本格的なオントロジ出力（Brick/REC/223P 等）は MVP-3 で上に重ねる段階構成とする。

### 7.2 非機能要求 (Non-Functional Requirements)

| ID | 区分 | 要求 | 優先度 | MVP | 原典 |
|----|------|------|:---:|:---:|:---:|
| PR-NF-001 | 規格適合 | ANSI/ASHRAE 135 / ISO 16484-5 に準拠する（対象版は要件定義書に従う） | M | 1 | 2 |
| PR-NF-002 | 試験規格 | ANSI/ASHRAE 135.1 / ISO 16484-6 を試験の指針とする | S | 2 | 2 |
| PR-NF-003 | 相互運用性 | YABE 等の標準 BACnet Explorer から北向きで探索・読書きできる | M | 1 | 16 |
| PR-NF-004 | 相互運用性 | 北向き BACnet を接続ゲートウェイ（Hono 等）/ Ditto / Building OS / BAS・BEMS が取り込めること | M | 1 | 1,16 |
| PR-NF-005 | 移植性 | Docker で配布し `docker compose up` で起動できる | M | 1 | 13 |
| PR-NF-006 | 移植性 | `network_mode: host` を推奨構成として動作する | S | 1 | 13 |
| PR-NF-007 | 自動化 | GitHub Actions 等の CI/CD に組み込み、統合テストを自動実行できる | S | 2 | 1 |
| PR-NF-008 | データ整合性 | 入力（SBCO）を唯一の真実とし、YAML を中間モデルとする | M | 1 | 22 |
| PR-NF-009 | 識別整合性 | `gateway_id` ≠ `bbc_id` を構造的に担保する | M | 1 | 4,22 |
| PR-NF-010 | 拡張性 | BACnet/SC・PICS・EDE 等を後付け可能なアーキテクチャとする | S | 2 | 22 |
| PR-NF-011 | 構成可能性 | `bbc_id` を設定ファイル/環境変数の双方で指定できる | M | 1 | 4 |
| PR-NF-012 | 使用性 | 主要操作を CLI で完結でき、エラーは原因が分かる形で報告する | M | 1 | 15 |
| PR-NF-013 | 観測性 | REST/CLI で現在のオブジェクト状態・値・有効な南向きバインディングを確認できる | S | 2 | 15,17 |
| PR-NF-014 | アーキテクチャ前提 | 上位連携は北向き BACnet/IP を接続ゲートウェイ（Hono 等）が取り込む前提で設計する | M | 2 | 新 |
| PR-NF-015 | 拡張性 | 南向きバインディングはプロトコル非依存の内部モデルから派生させ、プロトコル追加を容易にする | S | 2 | 新 |
| PR-NF-016 | 一貫性 | Simulator/Gateway/Combined の各モードで同一オブジェクトモデル・同一識別子体系を用いる | M | 2 | 新 |
| PR-NF-017 | 整合性 | 同一オブジェクトについて、南向き入力値と北向き BACnet `presentValue` が論理的に一致する | M | 2 | 新 |
| PR-NF-018 | 意味相互運用 | タグ語彙（BACnet 標準タグ＋Haystack）を一貫適用し、未知タグは検証で警告する | S | 2 | 新 |
| PR-NF-019 | 移植性 | Raspberry Pi（ARM/ARM64）上でネイティブに動作する | M | 1 | 新 |
| PR-NF-020 | 移植性 | Docker 非依存のネイティブ実行（uv 等）を提供する。Docker は推奨配布手段の一つであり必須ではない | M | 1 | 新 |

---

## 8. 制約条件 (Constraints)

| ID | 制約 |
|----|------|
| CON-1 | 入力ソースは SBCO 標準ポイントリストに限定する（他形式は中間で SBCO/YAML に正規化） |
| CON-2 | 1 ランタイムインスタンス = 1 Virtual B-BC（device-mapping mode に応じ 1..N の BACnet Device を公開。ADR-002/008/011）。ゲートウェイモードも崩さない |
| CON-3 | `gateway_id` を `bbc_id` に流用しない |
| CON-4 | BACnet 公開・サービス挙動は ANSI/ASHRAE 135 / ISO 16484-5 の範囲で実装する |
| CON-5 | 既定の BACnet トランスポートは BACnet/IP（BACnet/SC は将来対象） |
| CON-6 | 北向きは BACnet/IP に限定。上位系（Building OS）へは接続ゲートウェイ（Hono 等）経由を前提とし、上位プロトコルへの直接公開・直結を前提としない |
| CON-7 | MQTT / ZeroMQ / Web of Things / gRPC はサウスバウンド（バインディング）として位置づけ、北向きには用いない |
| CON-8 | `aggregated` device-mapping mode は Discovery 試験・Device 構成試験に使用しない（1 Device しか見えないため。これらは `multi-device` を使う。ADR-011） |

---

## 9. 前提・依存関係 (Assumptions & Dependencies)

- 入力となる SBCO 標準ポイントリストは `smartbuilding_datamodel_builder` リポジトリ（**原典**: https://github.com/smartbuilding-co-creation-organization/smartbuilding_datamodel_builder ）の仕様に準拠する。
- 実行環境として Raspberry Pi（ARM/ARM64, Linux）を含む。Docker が使えない/使わない環境でもネイティブに動作すること（PR-NF-019/020）。
- 上位経路として Eclipse Hono（接続ゲートウェイ／BACnet コネクタを含む）および Eclipse Ditto（デジタルツイン）が別途利用可能であること。
- 南向き試験のため、MQTT Broker、ZeroMQ/gRPC/WoT のデータ源（実機または擬似デバイス）が利用可能であること。
- 北向き確認のため、YABE 等の BACnet クライアントが利用可能であること。
- ホスト環境で BACnet/IP（既定 UDP 47808）が利用でき、必要に応じ `network_mode: host` が使えること。
- BBMD 越し試験では、対向側 BBMD 構成が整っていること。

---

## 10. 受け入れ基準 / 成功指標

### 10.1 受け入れ基準（要件定義書 16章の試験シナリオへトレース）

| 受入ID | 内容 | 対応TS | 対応要求 |
|--------|------|--------|----------|
| AC-1 | SBCO CSV を読み込み YAML を生成できる | TS-01 | PR-F-001,004 |
| AC-2 | YABE から Who-Is/I-Am で発見できる（北向き） | TS-02 | PR-F-020 |
| AC-3 | ReadProperty で presentValue/units/description を取得できる | TS-03 | PR-F-021 |
| AC-4 | ReadPropertyMultiple が機能する | TS-04 | PR-F-022 |
| AC-5 | WriteProperty が Writable のみ変更可能 | TS-05 | PR-F-023 |
| AC-6 | 南向き MQTT で受けた値が北向き BACnet presentValue に反映される | TS-06 | PR-F-084,083 |
| AC-7 | 北向き BACnet を接続ゲートウェイ（Hono 等）/ Ditto が取り込める | TS-07 | PR-F-088,089 |
| AC-8 | Building OS まで取得経路が通る | TS-08 | PR-NF-004,014 |
| AC-9 | 制御ループ（上位→北向き WriteProperty→南向きコマンド）が往復する | TS-09 | PR-F-023,083 |
| AC-10 | 別サブネット探索ができる | TS-10 | PR-F-041 |
| AC-11 | フォールトインジェクションが機能する | TS-11 | PR-F-031 |
| AC-12 | Combined モードで内部生成と南向きバインドのオブジェクトを同一 BACnet/IP に同時公開できる | （新）TS-12 想定 | PR-F-080,081 |
| AC-13 | ZeroMQ / WoT / gRPC の各南向きバインディングで取込・コマンド送出ができる | （新）TS-13 想定 | PR-F-085,086,087 |
| AC-14 | オブジェクトの `tags` プロパティを ReadProperty で取得でき、内容が **device_type/point_type の Brick クラスから導出**された語彙整合タグである。SBCO `tags` 列は `metadata.search_tags` に保持 | （新）TS-14 想定 | PR-F-016,017 / ADR-012 |
| AC-15 | 管理 UI から主要管理操作（状態確認・値書込・Fault・点リスト再読込・ログ閲覧）が完結できる | （新）TS-15 想定 | PR-F-052,053,054,055,056 |
| AC-16 | 初回利用者が初回ツアー／Help ページから概念（北向き/南向き・モード）と主要操作を理解できる | （新）TS-16 想定 | PR-F-057 |

### 10.2 成功指標 (Success Metrics)

| 指標 | 目標の方向性 |
|------|--------------|
| セットアップ時間 | SBCO リスト入手から仮想 B-BC 起動まで短時間で完了 |
| 試験再現性 | 同一入力で同一構成の B-BC を常に再生成できる |
| CI 統合 | 結合試験が CI で無人実行・合否判定できる |
| 相互運用 | YABE / 接続ゲートウェイ / Ditto / Building OS の北向き全経路で疎通 |
| プロトコル網羅 | 南向き MQTT / ZeroMQ / WoT / gRPC の各バインディングで双方向疎通 |
| 変換整合性 | 南向き入力と北向き BACnet 値の論理一致を試験で担保 |

---

## 11. リリース計画（MVP）

| フェーズ | 主要スコープ | 含む要求（抜粋） |
|---------|--------------|------------------|
| MVP-1 | SBCO→YAML→1 B-BC、Who-Is/I-Am、Read/ReadMultiple/WriteProperty、Docker 起動、YABE 北向き接続確認（Simulator） | PR-F-001〜007,010〜024,040,060〜062 / PR-NF-001,003,005,008,009 |
| MVP-2 | モード機構、南向きバインディング（MQTT/ZeroMQ/gRPC）、北向き BACnet の Hono/Ditto/Building OS 取込、COV、WritePropertyMultiple、REST、Fault、BBMD、管理者向け Web UI（EP-007） | PR-F-025〜031,041,050,052〜057,080〜085,087〜090,063 / PR-NF-002,007,010,013〜017 |
| MVP-3 | Web of Things 南向きバインディング、BACnet/SC、PICS/EDE 生成、BTL 適合支援、意味モデル出力 | PR-F-070〜073,086 |

---

## 12. リスクと対応

| リスク | 影響 | 対応方針 |
|--------|------|----------|
| BACnet 実装の規格逸脱 | 連携先と相互運用できない | 早期に YABE で北向き相互運用確認（AC-2〜5）を回す |
| `gateway_id`/`bbc_id` 混同 | 識別不整合・データ汚染 | 構造的に分離（PR-NF-009）し検証で機械的に担保 |
| object type 推定誤り | 連携先で型不一致 | BACnet 列があれば優先（PR-F-006）、検証で警告 |
| ネットワーク構成依存（host/BBMD） | 環境差で再現せず | 推奨構成を明示（PR-NF-006）、Compose で標準化 |
| 南向き 4 プロトコル個別実装による分散 | 重複・整合性低下 | プロトコル非依存の内部モデルから派生（PR-NF-015） |
| 南向き入力と北向き BACnet 値の不整合 | 試験結果の誤判定 | 単一オブジェクトモデル共有（PR-NF-016）と整合性試験（AC-13, PR-NF-017） |
| 上位接続ゲートウェイ（Hono 等）依存 | 上位連携が外部都合に左右される | Compose に試験用接続ゲートウェイ／BACnet コネクタを同梱し再現性を確保 |
| 将来規格（SC/PICS/EDE）の後付け困難 | 拡張時に再設計 | 拡張点を初期から分離（PR-NF-010） |

---

## 13. トレーサビリティ概要

本書の要求は要件定義書 v1.1 の各章にトレースする（各要求表の「原典」列を参照。「新」は本 PRD で新規定義）。

- 入力・変換: 5, 6, 15章
- B-BC / オブジェクト: 4, 7, 8, 10章
- サービス（北向き）: 9章
- シミュレーション: 11章
- ネットワーク: 12章
- 配布/Docker: 13, 14章
- API/MQTT/上位連携: 17, 18, 19章 + 新規（モード・南向きバインディング・北向き BACnet 前提）
- 試験: 16章
- 将来拡張: 19章
- 設計原則: 22章

### 補足：実装着手時に作成を推奨する下流設計書

本 PRD の下流として以下を別途作成することを推奨する（本書では要求のみ定義）。

- オブジェクトID採番仕様書（instance_no 自動生成ルール）
- SBCO→BACnet マッピング仕様書
- **サウスバウンド・バインディング仕様書（MQTT/ZeroMQ/WoT/gRPC ⇄ BACnet オブジェクトのトピック・スキーマ・型変換・双方向規約）**
- **運用モード設計書（Simulator/Gateway/Combined の起動・構成・モデル共有・南北の責務分離）**
- PICS/BIBBs 対応方針
- BACnet サービス実装優先度一覧
- Docker Compose 統合試験環境設計（YABE / MQTT Broker / Eclipse Hono / Eclipse Ditto / 南向き擬似デバイス含む）

---

## 付録A 用語集

| 用語 | 説明 |
|------|------|
| SBCO ポイントリスト | 本製品の唯一の入力ソースとなる標準ポイント定義 |
| B-BC | BACnet Building Controller。本製品が仮想的に生成し、または南向きデータを集約して表現する対象 |
| ノースバウンド | 本製品の上位インタフェース。常に BACnet/IP |
| サウスバウンド | 本製品の下位インタフェース。MQTT/ZeroMQ/WoT/gRPC のバインディング（ゲートウェイモードの主） |
| Simulator モード | SBCO から仮想 B-BC を生成し値を内部生成して北向き BACnet/IP に公開する動作 |
| Gateway モード | 南向きプロトコルのデータ源を BACnet オブジェクト化し北向き BACnet/IP に公開する動作 |
| Combined モード | Simulator と Gateway を同一インスタンスで併用する動作（runtime mode の値） |
| Runtime mode | 値の出所を決める軸: simulator / gateway / combined（ADR-005） |
| Virtual B-BC | 本製品が点リストから生成する仮想 B-BC。1 ランタイムインスタンス = 1 Virtual B-BC。device-mapping mode に応じ 1..N の BACnet Device を公開する |
| Device-mapping mode | SBCO device → BACnet device の写像を決める軸（runtime mode と直交）: aggregated / multi-device（+auto-partition）（ADR-011） |
| Aggregation（aggregated）モード | 点リスト全体を 1 BACnet Device に集約。ポイント網羅試験向け。Discovery 試験には使わない |
| Multi-Device モード | SBCO device ごとに BACnet Device を生成（実設備忠実）。Discovery/Gateway 試験向け |
| Auto-Partition | Device の object 数が上限超過時に複数 Virtual Device へ自動分割（RPM 性能対策） |
| `gateway_id` | 上位ゲートウェイ識別子。`bbc_id` とは別概念 |
| `bbc_id` | 仮想 B-BC の識別子。設定/環境変数で付与 |
| YAML 中間モデル | 入力と各モードの間に置く正規化モデル（全モードで共有） |
| Eclipse Hono | 上位接続ゲートウェイ。本製品の北向き BACnet を（BACnet コネクタ経由で）取り込み Building OS へ橋渡しする前提コンポーネント |
| Eclipse Ditto | デジタルツイン層。デバイス状態を Thing として表現し上位連携する |
| Web of Things (WoT) | W3C の Thing Description により Property/Action/Event を記述する相互運用フレームワーク。本製品では南向きの取込対象 |
| セマンティックタグ（BACnet `tags`） | 各 BACnet オブジェクトに付与する name＋任意 value のタグ集合（135-2016 以降の任意プロパティ）。**Brick クラスから導出**（ADR-012）。ビル OS 検索タグとは別概念 |
| SBCO 検索タグ | CSV `tags` 列の自由マーカー（`&&` 区切り・日本語可）。ビル OS 検索用。`metadata.search_tags` に保持し BACnet セマンティックタグには使わない |
| Brick / RealEstateCore (REC) | SBCO データモデルの基盤オントロジ。device_type→`brick:Equipment` サブクラス、point→`brick:Point`。意味モデル出力（PR-F-073）の正 |
| Project Haystack | 設備・点のタギング規約。BACnet 側タグ語彙の基盤。Brick クラスから Haystack タグを導出（ADR-012） |
| ASHRAE 223P | セマンティックタグ／データモデリングの上位標準。Haystack・Brick と調和。将来連携対象 |
| ZeroMQ | 軽量メッセージングライブラリ。南向きの低レイテンシなメッセージ配信に用いる |
| gRPC | HTTP/2 上の RPC フレームワーク。南向きの read/write/streaming に用いる |
| BBMD | BACnet Broadcast Management Device。サブネット越え探索に使用 |
| COV | Change of Value。値変化通知サービス |
| PICS / EDE | BACnet の適合・点表に関する標準成果物（将来対象） |
| YABE | Yet Another BACnet Explorer。北向き相互運用確認に使用する標準クライアント |
