# ADR-016: BOWS AMQP/Hono transport (optional) and down-link control

**Status:** Accepted  **Date:** 2026-06-07  **Origin:** EP-008 継続（#48 / #49, user request）

## Context

EP-008 の BOWS コネクタは telemetry-first（[[ADR-014]][[ADR-015]]）で、MQTT 上に
`bacnet-device-message` を publish するところまで実装済み。残る将来項目は 2 つ:

- **#48**: Eclipse Hono northbound への **AMQP 1.0** 送信。
- **#49**: Building OS からの **下り制御**（device-control）を BACnet WriteProperty に変換。

いずれも EP-008 のスコープ内だが、依存と方向性に設計判断が要る。AMQP 1.0 クライアント
（`python-qpid-proton`）は native（C, qpid-proton）を含み、Raspberry Pi / ARM ネイティブ実行と
最小依存（AGENTS.md §5）と緊張する。また下り制御は BOWS を **producer から producer+consumer** へ
拡張するため、B-BC の方向不変条件（[[ADR-005]]）との関係を明確化する必要がある。

## Decision

1. **AMQP 1.0 トランスポートは optional-extra＋遅延 import** とする。
   - `pyproject.toml` の `[project.optional-dependencies].amqp = ["python-qpid-proton>=0.39"]`。
   - `southbound/amqp.py` は proton を**メソッド内で遅延 import**し、未インストールでもモジュール
     import は成功する（`amqp://` を使うときだけ proton が必要）。CI/基本インストール・ARM は不変。
   - factory は `mqtt`/`zmq` と同様に `amqp` を遅延解決。チャネル `telemetry/{tenant}/{deviceId}` を
     Hono アドレス `/telemetry/{tenant}` ＋ メッセージ属性 `device_id`/`orig_address` に変換する
     （`Transport` インターフェースは不変）。
   - 認証/TLS は外部 secret（環境変数）から注入。既定資格情報は持たない（[[ADR-015]] §4 と整合）。

2. **下り制御は BOWS の consumer パスとして追加**する。
   - BOWS は `Transport.subscribe` で制御チャネルを購読し、コマンドを **BACnet WriteProperty** に
     変換して仮想 B-BC を制御する。これは **connector→B-BC の BACnet 書込**であり、B-BC 自身の
     北=BACnet/南=binding（[[ADR-005]]）は不変。BOWS が「上り=テレメトリ取得 / 下り=制御注入」の
     双方向コネクタになるだけで、B-BC のインターフェース方向は変えない。
   - 値の型解釈は **`ControlSchema`** に従う（下記）。`ControlType` は廃止し、配信は
     `gatewayId → connectionType` で内部解決する。

### ControlSchema（下り制御の値記述子）

```
ControlSchema {
  DataType: boolean | number | enum | text | object | other
  EnumLabels?   // enum / boolean のラベル
  Min?, Max?    // number の範囲
  MaxLength?    // text の最大長
  SchemaRef?    // object / other（任意・JSON Schema）
}
```

`DataType` で BACnet present-value へ変換する:

| DataType | BACnet 変換 |
|----------|-------------|
| boolean  | binary present-value（active/inactive、EnumLabels 任意） |
| number   | analog present-value（Min/Max でクランプ） |
| enum     | multi-state present-value（EnumLabels → 状態番号） |
| text     | CharacterString（MaxLength で切詰）。present-value 非対応型は対象外 |
| object/other | `SchemaRef`（JSON Schema）任意検証。当面スコープ外 |

書込対象は **writable オブジェクトのみ**（非 writable は writeAccessDenied、既存 enforcement と整合）。

## Consequences

- 基本インストールは AMQP 非依存のまま。`amqp://` 利用者のみ `uv sync --extra amqp`（または同等）で proton を入れる。
- 実 Hono / 実 AMQP ブローカ連携は `@pytest.mark.integration`＋手動受入。CI は InMemory/モックで自己完結（PR-NF-032 と整合）。
- 下り制御コマンドの**封筒**（runtime メッセージ）は原典 `gutp-building-os-oss` 確定までは 🔧 暫定とし、
  `ControlSchema` 自体はユーザー提示の定義を正とする。確定時に spec / fixtures を整合。
- spec `northbound-bows-buildingos.md` §4（AMQP）/§7（下り制御）を ✅/🔧 へ更新。PR-F-105/106 を進捗反映。
