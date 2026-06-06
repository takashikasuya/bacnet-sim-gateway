# ADR-001: SBCO 標準ポイントリストを唯一の入力ソースとする

- **Date:** 2026-06-06
- **Status:** Accepted
- **原典:** 要件定義書 §5, §22-1 / PRD CON-1, PR-NF-008

## Context

仮想 B-BC を生成するための入力ソースは複数あり得る（独自 JSON、手書き YAML、BACnet EDE など）。入力が複数あると、ポイント定義と BACnet モデルの整合を人手で取ることになり、マッピング誤り・属人化を招く（PRD 課題 P-4）。

## Decision

入力ソースを **SBCO 標準ポイントリスト（CSV/XLSX）に限定** する。他形式は中間で SBCO / YAML に正規化してから取り込む。SBCO リストは `smartbuilding_datamodel_builder` リポジトリの仕様に準拠する。

## Consequences

- 入力が単一になり、同一入力から同一構成を常に再生成できる（再現性）。
- SBCO リストの作成・管理は本製品の範囲外（外部依存）。
- 必須列の検証（PR-F-002）が品質ゲートになる。
- 関連: [[ADR-004]]（YAML 中間モデル）。
