# 通信シーケンス図 — 代表的なフロー

> 本書は bbc-sim の**代表的な通信**をシーケンス図（Mermaid）で示す設計ドキュメントです。
> 各図は実装（`src/bbc_sim/`）に対応し、関連する ADR を併記します。
> 関連: [`operating-modes.md`](operating-modes.md)（モード）, [`southbound-binding.md`](southbound-binding.md)（南向き）,
> [`northbound-bows-buildingos.md`](northbound-bows-buildingos.md)（BOWS）, `../memory/architecture.md`（全体像）。

## 不変条件（全図に共通）

- **北向き = BACnet/IP、南向き = MQTT/ZeroMQ/WoT/gRPC**（[[ADR-005]]）
- **single-loop asyncio・非ブロッキング**（[[ADR-010]]）
- **`gateway_id` ≠ `bbc_id`**（[[ADR-003]]）

| # | フロー | 主な構成要素 | モード |
|---|--------|--------------|--------|
| 1 | Simulator: 値生成 → 北向き読取 | `SimulationEngine` / `BBCApplication` | simulator |
| 2 | Gateway: 南向きテレメトリ取込 → 北向き読取 | `SouthboundManager` / `Transport` | gateway / combined |
| 3 | Gateway: 北向き書込 → 南向きコマンド送出 | `BBCApplication` / `SouthboundManager` | gateway / combined |
| 4 | 点リスト再読込（検証→差分→適用/再起動要求） | `PointListReloader` | 全モード |
| 5 | Admin UI / REST 状態取得 | `web.router` / `StatusProvider` | 全モード |
| 6 | BOWS: BACnet 取込 → Building OS へ MQTT 供給 | `BowsRunner` / `acquire` / `encoder` | EP-008 |

---

## 1. Simulator モード — 値生成と北向き読取

内部生成した値を BACnet オブジェクトに反映し、上位の BACnet クライアント（YABE / 接続ゲートウェイ）が
Who-Is / ReadProperty で取得する（`simulation/engine.py`, `simulator_runtime/app.py`）。

```mermaid
sequenceDiagram
    autonumber
    participant Eng as SimulationEngine
    participant Gen as ValueGenerator
    participant Obj as BACnet Object
    participant App as BBCApplication
    participant NB as Northbound client<br/>(YABE / Hono)

    Note over Eng,Obj: tick_seconds ごと（single loop, ADR-010）
    Eng->>Gen: next(t)
    Gen-->>Eng: value
    Eng->>Obj: presentValue = value<br/>(fault 抑止中はスキップ)

    Note over NB,App: 北向きは常に BACnet/IP（ADR-005）
    NB->>App: Who-Is
    App->>App: counters.who_is += 1
    App-->>NB: I-Am
    NB->>App: ReadProperty(present-value)
    App->>App: counters.read_property += 1
    App->>Obj: get presentValue
    Obj-->>App: value
    App-->>NB: value
```

## 2. Gateway モード — 南向きテレメトリ取込 → 北向き読取

南向き（MQTT/ZeroMQ）で受信した実データを `presentValue` に反映し、北向きへ投影する
（`southbound/binding.py`）。値の出所（source of record）は南向き。

```mermaid
sequenceDiagram
    autonumber
    participant Field as Field データ源
    participant T as Transport<br/>(MQTT / ZeroMQ)
    participant SM as SouthboundManager
    participant Obj as BACnet Object
    participant App as BBCApplication
    participant NB as Northbound client

    Note over SM,T: start() で await transport.start() → subscribe（ADR-013）
    Field->>T: publish telemetry
    T->>SM: _telemetry_handler(payload)
    SM->>SM: telemetry_to_present_value(spec, payload)
    alt 正常な payload
        SM->>Obj: presentValue = value
        SM->>SM: TelemetryRecord(quality="good")
    else 不正な payload（ValueError/TypeError/KeyError）
        SM->>SM: 警告ログ + quality="bad"<br/>（ループは継続, ADR-010）
    end
    NB->>App: ReadProperty(present-value)
    App-->>NB: value（南向き由来）
```

## 3. Gateway モード — 北向き書込 → 南向きコマンド送出

書込可能（writable）かつ command バインドされたオブジェクトへの北向き WriteProperty を、
南向きへコマンドとして送出する（`simulator_runtime/app.py`, `southbound/binding.py`）。

```mermaid
sequenceDiagram
    autonumber
    participant NB as Northbound client
    participant App as BBCApplication
    participant Obj as BACnet Object
    participant SM as SouthboundManager
    participant T as Transport
    participant Field as Field アクチュエータ

    NB->>App: WriteProperty(present-value)
    alt writable
        App->>App: counters.write_property += 1
        App->>Obj: presentValue = value
        opt command バインドあり
            App->>SM: on_command(oid_key, presentValue)
            SM->>SM: present_value_to_command(spec, value)
            SM->>T: publish(command channel, payload)
            T->>Field: command
        end
        App-->>NB: ack
    else 非 writable（Input 系）
        App->>App: counters.write_access_denied += 1
        App-->>NB: Error: writeAccessDenied
    end
```

## 4. 点リスト再読込 — 検証 → 差分 → 適用 or 再起動要求

`simulator.yaml` を再読込し、検証に通れば差分を分類してライブ適用、構造変更なら再起動要求を返す
（`rest/reload.py`, [[ADR-004]]）。検証失敗時は**何も変更しない**（安全ゲート）。

```mermaid
sequenceDiagram
    autonumber
    participant Op as Operator (UI/REST)
    participant API as REST /pointlist/reload
    participant R as PointListReloader
    participant Cfg as simulator.yaml
    participant App as BBCApplication
    participant Eng as SimulationEngine

    Op->>API: POST /pointlist/reload
    API->>R: apply()
    R->>Cfg: load_config(source)
    R->>R: bbc_id を保持（ADR-003）→ validate_config
    alt 検証エラー
        R-->>API: {status: validation_failed, errors}<br/>（無変更, ADR-004）
    else 構造変更（object_type/instance, device_id, network）
        R-->>API: {status: restart_required, diff, hint}
    else 非構造（ライブ適用）
        R->>App: add/delete object・description/tags 更新
        R->>App: set_writable_oids(new_cfg)
        R->>Eng: rebuild(new_cfg)
        R-->>API: {status: applied, diff}
    end
    API-->>Op: 結果
```

## 5. Admin UI / REST — 状態取得（北向きはローカル内省のみ）

ブラウザがサーバレンダリングの `/ui` を取得し、`StatusProvider` が live 状態を集約する
（`web/router.py`, `rest/status.py`）。**北向きはローカル内省のみで上流へプローブしない**（[[ADR-005]]）。

```mermaid
sequenceDiagram
    autonumber
    participant Br as Browser
    participant Web as /ui router (Jinja2)
    participant SP as StatusProvider
    participant App as BBCApplication
    participant SM as SouthboundManager

    Br->>Web: GET /ui/（Dashboard）
    Web->>SP: runtime_status / northbound_status / southbound_status
    SP->>App: counters・bind 状態（ローカル内省のみ, ADR-005）
    SP->>SM: status()（protocol 別 connected・point 別 quality）
    SP-->>Web: 集約状態
    Web-->>Br: HTML（サーバレンダリング）
    loop 自動更新（vanilla JS fetch, 5s）
        Br->>Web: GET /ui/partials/tiles
        Web-->>Br: HTML フラグメント
    end
```

## 6. BOWS コネクタ — BACnet 取込 → Building OS へ MQTT 供給

仮想 B-BC を BACnet クライアントとして読み、`bacnet-device-message` に変換して MQTT へ publish する
（`bows/runner.py`, `bows/acquire.py`, `bows/encoder.py`）。BOWS は **B-BC の下流の独立コネクタ**であり、
その MQTT 出力は connector→Building OS のリンク（[[ADR-014]]）。B-BC の方向不変条件は変えない（[[ADR-005]]）。

```mermaid
sequenceDiagram
    autonumber
    participant Run as BowsRunner<br/>(single loop)
    participant Acq as acquire()
    participant BBC as 仮想 B-BC<br/>(BACnet/IP)
    participant Enc as encode_device_message
    participant T as Transport (MQTT)
    participant BOS as Building OS

    Note over Run: interval ごと（ADR-010）
    Run->>Acq: acquire(client, target)
    Acq->>BBC: Who-Is
    BBC-->>Acq: I-Am（device instance）
    Acq->>BBC: ReadProperty(device, object-list)
    BBC-->>Acq: object identifiers
    Acq->>BBC: ReadPropertyMultiple(present-value, 全点)
    alt RPM 成功
        BBC-->>Acq: values（一括）
    else RPM 失敗 / 欠落点
        Acq->>BBC: ReadProperty(present-value) を点ごと
        BBC-->>Acq: value（レジリエンスのためのフォールバック）
    end
    Acq-->>Run: (device_instance, readings)
    alt readings なし（到達不能等）
        Run->>Run: publish スキップ + 警告
    else
        Run->>Enc: encode bacnet-device-message
        Enc-->>Run: JSON（ADR-015 スキーマ準拠）
        Run->>T: publish telemetry/{tenant}/{deviceId}
        T->>BOS: bacnet-device-message
    end
```

---

## 補足

- 図中のカウンタ（`counters.*`）は `BBCApplication` が北向きリクエストを非ブロッキングに計数するもので、
  `/status/northbound` と Admin UI に表示される（[[ADR-010]]）。
- COV（変化購読）通知は北向きの最適化であり本書の代表フローには含めない（`bacnet-service-priority.md` 参照）。
- モード切替（`/mode`）はライブ適用せず再起動要求を返す（[[ADR-010]]、`rest/api.py`）。
