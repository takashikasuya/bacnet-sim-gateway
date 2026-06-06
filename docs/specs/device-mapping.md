# 設備マッピングモード仕様（素案 v0.1）

> 出典: [[ADR-011]]。**runtime mode（operating-modes.md）とは直交する別軸**。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。

| 項目 | 内容 |
|------|------|
| 目的 | SBCO の device（行ごとの `device_id_bacnet`）を BACnet Device へどう写像するかを定義する |
| 関連要求 | PR-F-091〜094 / PR-NF-016 / [[ADR-011]] |

## 0. 2 つの mode 軸（混同禁止）✅

| 軸 | 値 | 何を決めるか |
|----|----|--------------|
| `runtime.mode` | simulator / gateway / combined | 値の出所（[[ADR-005]]） |
| `device_mapping.mode` | aggregated / multi-device | SBCO device → BACnet device の写像（本書） |

直交。例: `aggregated` + `gateway`、`multi-device` + `simulator` いずれも有効。

## 1. aggregated（MVP-1）✅

- 点リスト全体（複数 gateway_id を跨いでも可）→ **1 BACnet Device**（= Virtual B-BC）。全ポイントがその objects。
- BACnet Device id = CLI `--bacnet-device-id`（または YAML `bbc.device_id`）。
- `device_id` / `device_id_bacnet` は **objects[].metadata** に保持するが BACnet Device 分割には使わない。
- object instance は **このひとつの Device 内で再採番**（跨設備の `instance_no_bacnet` 衝突を回避。`object-id-numbering.md`）。
- 用途: Building OS / Ditto / MQTT のポイント網羅試験。
- **不可**: Discovery / Device 構成試験には使わない（1 Device しか見えない）。

## 2. multi-device（MVP-2）✅

- SBCO `device_id_bacnet`（無ければ `device_id`）ごとに **1 BACnet Device** を生成（実設備忠実）。
- `instance_no_bacnet` を尊重（device 内一意）。`object_type_bacnet` を優先。
- 1 ランタイムインスタンスが N Device を公開 → **BACnet 仮想ネットワーク + ルータ**でアドレッシング（BBMD / PR-F-041 と同一マイルストーン）。
- 用途: Gateway 開発・Discovery 試験（YABE で N 台見える）。

## 3. auto-partition（MVP-3）🔧

- ある Device の object 数が `limits.max_objects_per_device`（既定 1000）を超えたら `Virtual Device #1..#N` に自動分割。
- 分割後の Device id 採番・instance 再スコープ規則は `object-id-numbering.md` で定義（❓ 既定の基底+オフセット規則）。
- 目的: 巨大 Device での `ReadPropertyMultiple` 性能劣化の回避。

## 4. 設定例

```yaml
device_mapping:
  mode: aggregated        # aggregated | multi-device
  auto_partition: true    # MVP-3
limits:
  max_objects_per_device: 1000
```

## 5. 未決事項（❓）

- auto-partition の Device id / instance 再採番の既定規則
- multi-device の仮想ネットワーク番号・ルータ構成・ホスト上のアドレス割当
- aggregated 再採番時に元 `instance_no_bacnet` をどう metadata 保持するか
