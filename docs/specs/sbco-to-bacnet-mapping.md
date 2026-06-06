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
| tags | objects[].tags（BACnet `tags` プロパティ）＋ metadata.tags |
| device_id_bacnet | （採番）`object-id-numbering.md` を参照 |
| instance_no_bacnet | （採番）`object-id-numbering.md` を参照 |
| object_type_bacnet | objects[].object_type（**存在時は §2 の推定より優先**） |

## 2. object type 推定 ✅（[[ADR-007]]）

`object_type_bacnet` 列があれば最優先。無ければ point_type/データ型 ＋ writable から推定（要件定義書 §6）。

| データ型 | writable | object type | enum |
|----------|----------|-------------|:---:|
| float | false | analogInput | 0 |
| float | true | analogValue | 2 |
| bool | false | binaryInput | 3 |
| bool | true | binaryValue | 5 |
| enum | false | multiStateInput | 13 |
| enum | true | multiStateValue | 19 |

- ❓ `analogOutput(1)/binaryOutput(4)/multiStateOutput(14)` を採用する条件（point_specification に出力指定がある場合など）は要決定。現案では Value 系に集約。
- ❓ SBCO の `point_type` / `point_specification` から float/bool/enum を判定する正規化規則の確定（型名の表記ゆれ吸収）。

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
- activeText/inactiveText 既定 = "Active"/"Inactive"（❓ SBCO 由来があれば優先）。
- polarity 既定 = normal。

### 4.4 Multi-state（MI/MO/MV）
`numberOfStates, stateText`
- enum 値集合 → numberOfStates と stateText[] に展開。
- ❓ SBCO 上の enum 定義（状態ラベル一覧）の格納列・形式の確定。

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

SBCO `tags` 列を BACnet ネイティブの `tags` プロパティ（135-2016 以降の任意プロパティ）に射影する。各タグは name＋任意 value（BACnetNameValue 相当）。内部利用・互換のため `metadata.tags` にも併記する。

### 語彙ポリシー（既定：BACnet 標準タグ ＋ Haystack）✅
- **BACnet 標準タグ**: 135 が定義するタグ名を name のみのタグ（marker）として付与。
- **Project Haystack**:
  - marker タグ（例 `sensor`, `temp`, `air`, `discharge`）→ name のみのタグ。
  - name:value タグ（例 `unit:"°C"`, `equipRef:"AHU-01"`）→ name＋value のタグ。
- 名前空間の分離（標準 / Haystack / 独自）の表現方法は 🔧（namespace 機構は要決定）。
- ❓ 採用する BACnet 標準タグ集合と Haystack タグ集合の確定版（対応表を別表 CSV で管理）。

### SBCO `tags` 列の構文（既定）🔧
- 区切り: カンマ区切り（例 `sensor,temp,air,discharge,unit:°C`）。
- `name:value` は value 付きタグ、`name` 単独は marker。
- ❓ 区切り文字・エスケープ・大小文字規則の確定。

### 生成規則 ✅
- 決定的（同一 `tags` 列 → 同一 `tags` プロパティ）。
- 重複は正規化（重複除去）。
- 未知タグ（標準でも Haystack でもない）は **検証で警告**（§7）し、独自タグとして保持。

### 例
入力 `tags = sensor,temp,air,discharge,unit:°C`
```yaml
tags:
  - { name: sensor }
  - { name: temp }
  - { name: air }
  - { name: discharge }
  - { name: unit, value: "°C" }
```

## 7. 検証ルール（validate / validate-point-list）✅

- 必須列の存在（要件定義書 §5）。
- point_id の一意性。
- writable の真偽値正規化（true/false/1/0/yes/no 等）。
- object_type_bacnet が既知列挙であること。
- unit が対応表にあること（無ければ警告）。
- 採番衝突（`object-id-numbering.md` §6）。
- タグ語彙: 標準タグ／Haystack のいずれにも無いタグは警告（独自タグとして許容）。

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
