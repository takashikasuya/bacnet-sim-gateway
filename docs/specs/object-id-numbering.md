# オブジェクトID採番仕様書（素案 v0.1）

> 出典: PRD §13補足 / 要件定義書 §6, §7。関連: [[ADR-003]]（id分離）, [[ADR-004]]（YAML固定化）, [[ADR-007]]（object type 推定）。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。

| 項目 | 内容 |
|------|------|
| 目的 | SBCO ポイントリストから BACnet の Device instance / Object instance を**決定的**に採番する規則を定義する |
| 関連要求 | PR-F-005, PR-F-006, PR-F-010, PR-F-012 / PR-NF-008, PR-NF-009, PR-NF-016 |
| 前提 | BACnet instance は 22bit（0〜4194302）。Device Object も同範囲 |

## 1. 採番対象

| 対象 | 採番先 | 範囲 |
|------|--------|------|
| Device instance | Device Object の objectIdentifier | 0〜4194302 |
| Object instance | 各 Analog/Binary/Multi-state オブジェクト | object type 単位で 0〜4194302 |

> BACnet では objectIdentifier は (objectType, instance) の組で一意。したがって instance は**object type 単位で一意**であればよい。

## 2. Device instance 採番 ✅

優先順位（上から評価し最初に確定したものを採用）。

1. CLI `--bacnet-device-id` で明示指定された値
2. SBCO 列 `device_id_bacnet` が存在する場合はその値
3. `bbc_id` から決定的にハッシュ→範囲射影（フォールバック）

```
device_instance =
  cli_device_id
  ?? sbco.device_id_bacnet
  ?? (crc32(bbc_id) mod 4_000_000) + 1   # フォールバック（衝突時は §6）
```

- ❓ フォールバックのハッシュ関数・範囲は要決定（crc32 / 範囲 1〜4,000,000 は暫定）。

## 3. Object instance 採番 ✅

優先順位。

1. SBCO 列 `instance_no_bacnet` が存在する場合はその値（最優先・PR-F-006）
2. 自動採番（下記）

### 3.1 自動採番ルール

- object type ごとに独立した採番空間を持つ。
- 同一 object type 内で、**安定ソートキー**昇順に 1 から連番付与する。
- 安定ソートキーの既定は `point_id`（文字列昇順）。同値時は `local_id`、さらに入力行順をタイブレークに用いる。

```
for ot in object_types:
    pts = [p for p in points if p.object_type == ot and p.instance_no_bacnet is None]
    pts.sort(key=lambda p: (p.point_id, p.local_id, p.row_index))
    n = 1
    used = { p.instance_no_bacnet for p in points if p.object_type == ot and p.instance_no_bacnet is not None }
    for p in pts:
        while n in used: n += 1     # 明示指定との衝突回避
        p.object_instance = n
        used.add(n); n += 1
```

### 3.2 採番空間（任意のバンド方式）🔧

可読性のため object type ごとに開始オフセットを設ける案（既定は無効=オフセット0）。

| object type | enum | 既定オフセット案 |
|-------------|:---:|:---:|
| analogInput | 0 | 0 |
| analogOutput | 1 | 0 |
| analogValue | 2 | 0 |
| binaryInput | 3 | 0 |
| binaryOutput | 4 | 0 |
| binaryValue | 5 | 0 |
| multiStateInput | 13 | 0 |
| multiStateOutput | 14 | 0 |
| multiStateValue | 19 | 0 |

- ❓ バンド（例: AI=1〜、AV=10000〜）を採用するか要決定。採用時も §3.1 の決定性は維持する。

### 3.3 device-mapping mode との関係 ✅（[[ADR-011]]）

instance 採番空間は **(virtual) BACnet Device 単位**にスコープする。

- **aggregated**: 全ポイントが 1 Device に集約されるため、跨設備で `instance_no_bacnet` が衝突しうる。この mode では **明示 `instance_no_bacnet` を採用せず §3.1 で再採番**する（元値は `metadata.instance_no_bacnet_src` に保持）。
- **multi-device**: Device ごとに採番空間が独立。`instance_no_bacnet` を尊重（device 内一意）。
- **auto-partition**: 分割後の各 Virtual Device に Device id を付与し、instance 空間を partition ごとに再スコープ（❓ 基底+オフセット規則は要確定）。

## 4. 決定性・冪等性 ✅

- 同一入力（同一 SBCO ＋同一 CLI 引数）からは**常に同一の instance** を生成する。
- 入力の行追加・削除・並べ替えに対する安定性を持たせるため、行順ではなく `point_id` 主体のソートキーを用いる（§3.1）。
- 生成結果は YAML に固定化され、以後はランタイムの真実となる（再採番しない）。

## 5. 識別子の分離 ✅（最重要原則 / [[ADR-003]]）

- `gateway_id` は採番に一切使用しない（上位ゲートウェイ識別子のため）。
- `bbc_id` はフォールバック Device instance の導出にのみ利用しうるが、Object instance には使用しない。

## 6. 衝突検出 ✅

- 明示指定（`instance_no_bacnet` / `device_id_bacnet`）の重複は**エラー**として停止。
- 自動採番は §3.1 で明示値と衝突しないことを保証。
- Device instance の重複（同一ネットワーク上）は実行時にも検出し警告する（🔧 範囲は別途）。

## 7. 例

入力（抜粋）

| point_id | object_type | instance_no_bacnet | local_id |
|----------|-------------|:---:|----------|
| AHU01_RAT | analogInput | (空) | 2 |
| AHU01_SAT | analogInput | (空) | 1 |
| AHU01_FAN | binaryValue | 5 | 3 |
| AHU01_RUN | binaryValue | (空) | 4 |

採番結果（device_id=1001）

| point_id | object | 採番根拠 |
|----------|--------|----------|
| Device | device,1001 | CLI `--bacnet-device-id 1001` |
| AHU01_RAT | analogInput,2 | 自動（SAT より point_id 昇順で後） |
| AHU01_SAT | analogInput,1 | 自動 |
| AHU01_FAN | binaryValue,5 | 明示 `instance_no_bacnet=5` |
| AHU01_RUN | binaryValue,1 | 自動（5 と衝突せず） |

## 8. 未決事項（❓）

- フォールバック Device instance の算出方式と既定範囲
- バンド採番の採否
- 複数 B-BC を同一ネットワークに並べる際の Device instance 割当ポリシー（外部入力 or 採番）
