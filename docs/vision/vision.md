# Vision — SBCO BACnet B-BC Simulator / Gateway

> 出典: PRD v1.5 §1–2（`../backlog/PRD-v1.5.md`）。本ファイルは「なぜ作るか」の要約。

## Why we build this

スマートビルディング連携基盤（BACnet 接続ゲートウェイ → Building OS）の開発・結合試験には、実設備の BACnet コントローラ（B-BC）が要る。しかし実 B-BC は **開発初期に存在せず・調達が高く・物理アクセスが必要で CI に乗らず・異常系を意図的に再現しにくい**。これが上流開発の直列化と回帰検証コストを生む。

`bacnet-sim-gateway` は **SBCO 標準ポイントリスト 1 つ** を唯一の入力として、実設備の代替かつプロトコル変換ハブとなる。

## Vision statement

> 実設備がなくても、SBCO 標準ポイントリスト 1 つから標準準拠の仮想 B-BC を **BACnet/IP（北向き）** で公開し（Simulator）、さらに同じ BACnet オブジェクトを **MQTT / ZeroMQ / Web of Things / gRPC（南向き）** のデータ源にバインドして実データを BACnet 化して上位へ供給できる（Gateway）。上位系は Eclipse Hono 等の接続ゲートウェイ経由でこの BACnet を取り込み、Building OS まで繋がる。

## 関連コンポーネント — BOWS コネクタ（EP-007）

仮想 B-BC の北向き BACnet を **クライアントとして取り込み**、テレメトリを **MQTT / AMQP** に変換して
**Building OS（`gutp-building-os-oss`）** へ供給する **BACnet→Building OS コネクタ（BOWS）** を本リポジトリの
構成要素とする（[[ADR-014]]）。これは仮想 B-BC の下流に位置する別レイヤの消費者であり、B-BC 自身の
インターフェース方向（北=BACnet/南=binding, [[ADR-005]]）は変えない。スキーマは Building OS の
BACnet ネイティブ形式（`bacnet-device-message`）に従う（[[ADR-015]] / `../specs/northbound-bows-buildingos.md`）。

## Success looks like

- SBCO リスト入手から仮想 B-BC 起動まで短時間（`docker compose up` で起動）
- 同一入力で同一構成の B-BC を常に再生成できる（再現性）
- 結合試験が CI で無人実行・合否判定できる
- YABE / 接続ゲートウェイ / Ditto / Building OS の北向き全経路で疎通
- 南向き MQTT / ZeroMQ / WoT / gRPC の各バインディングで双方向疎通

## Out of scope (Non-Goals)

- 実制御アルゴリズムの忠実再現（対象は**通信・データ・連携の試験**）
- BTL 正式認証の取得そのもの（適合**支援**までを将来対象）
- SBCO ポイントリスト自体の作成・管理（外部リポジトリを入力として扱う）
- Building OS（`gutp-building-os-oss`）**本体の実装**（コネクタが供給する相手であり、改修対象ではない）
- Building OS 側の point_id オントロジ登録（OxiGraph）— コネクタは整合する識別子を発行するのみ
- ゲートウェイの本番 HA・大規模運用（当面）

> **スコープ変更（EP-007）**: 旧版で Non-Goal としていた「上位接続ゲートウェイ自体の実装」は、
> BACnet→Building OS テレメトリ・コネクタ（BOWS）として**スコープ内に変更**した（[[ADR-014]]）。
