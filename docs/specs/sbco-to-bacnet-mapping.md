# SBCO→BACnet マッピング仕様書（素案 v0.1）

> 出典: 要件定義書 §5, §6, §10。関連: [[ADR-007]]（object type 推定）, [[ADR-006]]（tags）, `object-id-numbering.md`（採番）。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。

| 項目 | 内容 |
|------|------|
| 目的 | SBCO 標準ポイントリストの各列を BACnet オブジェクト/プロパティへ変換する規則を定義する |
| 関連要求 | PR-F-004〜007, PR-F-013, PR-F-014 / PR-NF-008 |
| 原典 | 要件定義書 §5, §6, §10 |

## 1. 列マッピング ✅

要件定義書 §6 を基準とする。

| SBCO 列 | YAML / BACnet 反映先 |
|---------|----------------------|
| gateway_id | metadata.gateway_id（**識別のみ。BACnet には使わない**） |
| device_id | metadata.device_id |
| device_name | metadata.device_name |
| device_type | metadata.device_type |
| point_id | objects[].point_id（内部キー） |
| point_name | objects[].object_name |
| writable | objects[].writable（object type 推定とプロパティ writability に使用） |
| unit | objects[].units（§3 で BACnet enum に変換） |
| interval | objects[].update.interval |
| building | metadata.building |
| floor | metadata.floor |
| installation_area | metadata.installation_area |
| description | objects[].description |
| min_pres_value | objects[].minPresValue |
| max_pres_value | objects[].maxPresValue |
| tags | **metadata.search_tags**（ビル OS 検索タグ。`&&` 区切り・verbatim・日本語可）。**BACnet `tags` プロパティの生成源ではない**（§6.5） |
| device_type | metadata.device_type ＋ **Brick Equipment クラス**へ写像（§6.5 / [[ADR-012]]） |
| point_type | metadata.point_type ＋ **Brick Point クラス**へ写像（§6.5 / [[ADR-012]]） |
| labels | objects[].state_text / activeText・inactiveText（`&&` 区切り。§4.3/§4.4） |
| scale | objects[].scale（Present Value への倍率。§6 / southbound でも使用） |
| target_area | metadata.target_area |
| supplier | metadata.supplier |
| owner | metadata.owner |
| local_id | gateway: **南向きアドレス第一源**（`southbound-binding.md` §6）/ simulator: metadata のみ |
| device_id_bacnet | （採番）`object-id-numbering.md` を参照 |
| instance_no_bacnet | （採番）`object-id-numbering.md` を参照 |
| object_type_bacnet | objects[].object_type（**存在時は §2 の推定より優先**） |

## 2. object type 決定 ✅（[[ADR-007]]）

> 重要: `point_type` は意味的プロファイル名でデータ型ではない。型は **`object_type_bacnet` の明示が本筋**。推定はフォールバックで、走ったら**警告**してポイントリスト明示化を促す。

**優先順位:**

1. **`object_type_bacnet` を正規化して採用**（最優先）。表記ゆれを吸収:

   | SBCO 表記（例） | YAML | enum |
   |----------------|------|:---:|
   | `Analog-Input` / `analogInput` / `AI` | analogInput | 0 |
   | `Analog-Output` | analogOutput | 1 |
   | `Analog-Value` | analogValue | 2 |
   | `Binary-Input` | binaryInput | 3 |
   | `Binary-Output` | binaryOutput | 4 |
   | `Binary-Value` | binaryValue | 5 |
   | `Multi-state-Input` | multiStateInput | 13 |
   | `Multi-state-Output` | multiStateOutput | 14 |
   | `Multi-state-Value` | multiStateValue | 19 |

2. 無ければ**推定（＋警告「object_type_bacnet を明示してください」）:**

   | 条件 | 種別 |
   |------|------|
   | `labels` 数 ≥ 3 | MultiState |
   | `labels` 数 == 2 | Binary |
   | 数値 `unit` あり / `point_specification` ∈ {Measurement, Metering, Setpoint} | Analog |
   | `point_specification` ∈ {Status, Alarm} かつ数値 unit 無し | Binary |
   | 上記いずれも非該当 | Analog（フォールバック）＋ **警告** |

3. **Input ⇄ Value**: `writable=false`→Input、`writable=true`→Value。
4. **Output 系（AO/BO/MO）は推定で生成しない**。必要なら `object_type_bacnet` で明示する。
5. **整合性警告**: `point_specification` ∈ {Command, Setpoint} なのに `writable=false` 等の矛盾は警告。

## 3. 単位マッピング（unit → BACnet Engineering Units）🔧

BACnet `units`（ASHRAE 135 の列挙）へ変換する。代表例（暫定）。

| SBCO unit（例） | BACnet units |
|-----------------|--------------|
| ℃ / degC / Celsius | degreesCelsius (62) |
| % | percent (98) |
| %RH | percentRelativeHumidity (29) |
| kW | kilowatts (48) |
| kWh | kilowattHours (19) |
| Pa | pascals (53) |
| m3/h | cubicMetersPerHour (135) |
| ppm | partsPerMillion (96) |
| (無単位/bool/enum) | noUnits (95) |

- 未知単位は `noUnits` にフォールバックし**警告**。完全な対応表は別表（CSV）で管理 🔧。

## 4. 型別必須プロパティの生成 ✅

要件定義書 §10 に従い、object type ごとに必須プロパティを付与する。

### 4.1 Common（全オブジェクト）
`objectIdentifier, objectName, objectType, description, presentValue, statusFlags, eventState, outOfService`

### 4.2 Analog（AI/AO/AV）
`units, minPresValue, maxPresValue, resolution`
- minPresValue/maxPresValue は SBCO 列があれば採用、無ければ既定（❓ 既定値要決定）。
- resolution 既定（❓ 例: 0.1）。

### 4.3 Binary（BI/BO/BV）
`activeText, inactiveText, polarity`
- **`labels` が 2 個**のとき: `labels[0]`→inactiveText(0), `labels[1]`→activeText(1)（例 `開&&閉`）。原典準拠。
- `labels` 無しの既定 = "Inactive"/"Active"。
- polarity 既定 = normal。

### 4.4 Multi-state（MI/MO/MV）
`numberOfStates, stateText`
- **`labels`（`&&` 区切り）** を状態ラベル源とする。`numberOfStates = len(labels)`、`stateText = labels`（0,1,2… に対応）。原典 pointlist.md「ラベル」節準拠。
- **`labels` が 3 個以上** → multi-state、**2 個** → binary（§4.3）、というラベル数による判別が可能（object type 推定。ADR-007 改訂で扱う）。

## 5. writable とプロパティ書込可否 ✅

- `writable=true` → object type を Value/Output 系にし、presentValue を WriteProperty 可とする。
- `writable=false` → Input 系。presentValue は外部書込不可（南向き/シミュレーションでのみ更新）。
- Command Priority（priorityArray / relinquishDefault）の扱いは ❓（Value 系で priorityArray を持たせるか要決定）。

## 6. update（値更新）マッピング ✅

| SBCO | YAML |
|------|------|
| interval | objects[].update.interval（秒） |
| （モード） | objects[].update.mode（simulator 時: random_walk/sinusoidal/replay/scenario） |

- gateway モードでは update.mode より南向き binding が優先（`southbound-binding.md`・`operating-modes.md` 参照）。

## 6.5 セマンティックタグ（`tags` プロパティ）✅（[[ADR-006]]）

**2 つの「タグ」を区別する（[[ADR-012]]）:**
- **BACnet セマンティックタグ** = `tags` BACnet プロパティ（135-2016 以降の任意プロパティ、BACnetNameValue）。**生成源は Brick クラス**（device_type/point_type）。本節の主対象。
- **SBCO 検索タグ** = CSV の `tags` 列（`温度&&会議室` 等の自由マーカー）。**ビル OS 検索用で別概念**。`metadata.search_tags` に verbatim 保持し、BACnet セマンティックタグには用いない。

### 語彙ポリシー（既定：BACnet 標準タグ ＋ Haystack）✅
- **BACnet 標準タグ**: 135 が定義するタグ名を name のみのタグ（marker）として付与。
- **Project Haystack**:
  - marker タグ（例 `sensor`, `temp`, `air`, `discharge`）→ name のみのタグ。
  - name:value タグ（例 `unit:"°C"`, `equipRef:"AHU-01"`）→ name＋value のタグ。
- 名前空間の分離（標準 / Haystack / 独自）の表現方法は 🔧（namespace 機構は要決定）。
- ❓ 採用する BACnet 標準タグ集合と Haystack タグ集合の確定版（対応表を別表 CSV で管理）。

### BACnet セマンティックタグの生成（Brick 由来）✅（[[ADR-012]]）
- `device_type` → **Brick Equipment クラス**、`point_type` → **Brick Point クラス**へ写像（SBCO オントロジは Brick/REC ベース）。
- Brick クラス → Haystack タグ集合を **明示の写像テーブル（seed）** で導出（自動推測しない）。例: 室温センサ → `point, sensor, temp, air, zone`。
- 決定的（同一 device_type/point_type → 同一タグ集合）。重複は正規化。
- 生成が Brick 由来のため出力は語彙整合的。手書き等で語彙外タグが現れた場合のみ §7 で警告し独自タグとして保持。
- ❓ device_type/point_type → Brick クラス → Haystack タグの seed 写像範囲（MVP-2）。

### SBCO `tags` 列（= ビル OS 検索タグ。BACnet タグではない）✅
- `metadata.search_tags` に格納。区切りは **`&&`**（原典 pointlist.md。CSV のためカンマ不可。例 `温度&&会議室`）。`labels` も同じ `&&` 区切り。
- 語彙・構文の検証はしない（原典は語彙指定なし、日本語可）。verbatim 保持・重複除去のみ。

## 7. 検証ルール（validate / validate-point-list）✅

- 必須列の存在（要件定義書 §5）。
- point_id の一意性。
- writable の真偽値正規化（true/false/1/0/yes/no 等）。
- object_type_bacnet が既知列挙であること。
- unit が対応表にあること（無ければ警告）。
- 採番衝突（`object-id-numbering.md` §6）。
- BACnet セマンティックタグは Brick 由来のため語彙整合的。`device_type`/`point_type` に Brick 写像が無い場合は警告。
- SBCO `tags` 列（検索タグ → `metadata.search_tags`）は語彙検証しない（verbatim）。

## 8. 例

入力行
```
gateway_id=gw-001, device_id=ahu-01, point_id=AHU01_SAT,
point_name=Supply Air Temperature, writable=false, unit=degC,
min_pres_value=0, max_pres_value=50, building=building-a, floor=10
```
生成（YAML 抜粋）
```yaml
- point_id: AHU01_SAT
  object_type: analogInput      # float + ReadOnly
  object_instance: 1            # object-id-numbering.md で採番
  object_name: Supply Air Temperature
  present_value: 0.0
  units: degreesCelsius
  min_pres_value: 0
  max_pres_value: 50
  writable: false
  metadata: { gateway_id: gw-001, device_id: ahu-01, building: building-a, floor: 10 }
```
