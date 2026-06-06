# PICS / BIBBs 対応方針（素案 v0.1）

> 出典: 要件定義書 §8, §9, §10, §19。関連: [[ADR-006]]（tags）, `bacnet-service-priority.md`。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。

| 項目 | 内容 |
|------|------|
| 目的 | 対応 BIBBs を定義し、PICS（Protocol Implementation Conformance Statement）出力方針を示す |
| 関連要求 | PR-F-072, PR-NF-001, PR-NF-002 |
| 規格 | ANSI/ASHRAE 135 Annex K（BIBBs）/ Annex L（Device Profile）, ISO 16484-5 |

## 1. 方針 ✅
- 本製品は **B-BC（BACnet Building Controller）相当**を目指すが、当面は**サブセット適合**を明示する（フル B-BC 準拠は段階的）。
- 実装済みサービス（`bacnet-service-priority.md`）から BIBBs を機械的に導出して PICS/EDE を生成できる構造とする（PR-F-072, MVP-3）。

## 2. 対応 BIBBs（サービス対応表）✅

本製品は主に **B（実行側）** の BIBBs を提供する。

| 機能領域 | BIBB | 内容 | 対応サービス | フェーズ |
|----------|------|------|--------------|:---:|
| Data Sharing | DS-RP-B | ReadProperty 実行 | PR-F-021 | MVP-1 |
| Data Sharing | DS-RPM-B | ReadPropertyMultiple 実行 | PR-F-022 | MVP-1 |
| Data Sharing | DS-WP-B | WriteProperty 実行 | PR-F-023 | MVP-1 |
| Data Sharing | DS-WPM-B | WritePropertyMultiple 実行 | PR-F-025 | MVP-2 |
| Data Sharing | DS-COV-B | SubscribeCOV / ConfirmedCOV 通知 | PR-F-028 | MVP-2 |
| Data Sharing | DS-COVU-B | UnconfirmedCOV 通知 | PR-F-028 | MVP-2 |
| Device Mgmt | DM-DDB-B | Who-Is 受信 / I-Am 応答 | PR-F-020 | MVP-1 |
| Device Mgmt | DM-DOB-B | Who-Has 受信 / I-Have 応答 | PR-F-026 | MVP-2 |
| Device Mgmt | DM-DCC-B | DeviceCommunicationControl 実行 | PR-F-027 | MVP-2 |
| Device Mgmt | DM-RD-B | ReinitializeDevice 実行 | PR-F-027 | MVP-2 |
| Device Mgmt | DM-TS-B | TimeSynchronization 実行 | PR-F-027 | MVP-2 |

- ❓ DM-UTC-B（UTCTimeSynchronization）採否。
- 将来（MVP-3 以降）: Scheduling（SCHED-I-B）、Trending（T-VMT-I-B / T-ATR-B）、Alarm/Event（AE-*）を追加（PR-F-070, §19）。
- セマンティックタグ: 当面は BACnet ネイティブ `tags`（標準タグ＋Haystack、MVP-2、PR-F-016〜018）。MVP-3 で ASHRAE 223P／Brick グラフへの対応付けを追加（PR-F-073）。

## 3. 対応オブジェクト型 ✅
Device / Analog Input/Output/Value / Binary Input/Output/Value / Multi-state Input/Output/Value（要件定義書 §8）。
将来: Schedule, Trend Log, Notification Class, Calendar, Accumulator。

## 4. 対応プロパティ ✅
要件定義書 §10 の Common / Analog / Binary / Multi-state 必須プロパティを基準（`sbco-to-bacnet-mapping.md` §4）。
- 加えて、各オブジェクトの **`tags` プロパティ**（セマンティックタグ、135-2016 以降の任意プロパティ）を提供する（PR-F-016）。語彙は BACnet 標準タグ＋Haystack（`sbco-to-bacnet-mapping.md` §6.5）。対応する Protocol_Revision を PICS に明記する。

## 5. データリンク層・セグメンテーション ✅
- データリンク: BACnet/IP（Annex J）。BBMD / Foreign Device 対応（PR-F-041）。
- セグメンテーション対応: ❓（送受信ともサポートするか、Both/Transmit/No を要決定）。
- 最大 APDU 長 / Max Segments: ❓ 既定値を決定（例: 1476 / segmented-both）。
- 将来: BACnet/SC（Annex YY）。

## 6. キャラクタセット / 文字コード ✅
- objectName/description 等の文字集合: UTF-8 を既定（❓ ISO 10646(UTF-8) を PICS 上で宣言）。

## 7. PICS 出力方針（MVP-3）🔧
- 実装登録情報（対応 BIBBs / オブジェクト / プロパティ / データリンク / 文字集合）をメタデータとして保持。
- `bbc-sim export-pics`（将来 CLI）で標準様式に整形出力。
- EDE / IEIEJ CSV も同メタデータから派生（PR-F-072）。

## 8. 適合表明（暫定テンプレート）🔧
| 項目 | 値（暫定） |
|------|-----------|
| Vendor Name | SBCO Simulator |
| Vendor Identifier | 999（要件定義書 §14） |
| Product Name | Virtual BBC |
| BACnet Protocol Revision | ❓（対象 135 版に整合） |
| Device Profile | B-BC（サブセット適合を明記） |
| Data Link | BACnet/IP |

## 9. 未決事項（❓）
- 目標とする ASHRAE 135 の版・Protocol Revision の確定（要件定義書では 135-2024 を参照）
- `tags` プロパティの property-identifier と BACnetNameValue 構造を対象版で確認
- 採用する BACnet 標準タグ集合と Haystack タグ集合の確定、名前空間表現
- ASHRAE 223P 連携の段階（MVP-3）と タグ→223P グラフ写像の方針
- セグメンテーション/最大 APDU の既定
- DM-UTC-B など任意 BIBB の採否
- BTL 適合支援（PR-F-071 系）のスコープ
