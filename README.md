# bbc-sim — SBCO BACnet B-BC Simulator / Gateway

SBCO 標準ポイントリストを唯一の入力として仮想 BACnet B-BC を生成し、**BACnet/IP（北向き）** で公開する統合シミュレータ兼プロトコル変換ゲートウェイ。

- 設計ドキュメント: `docs/`（読む順: `AGENTS.md` → `docs/vision` → `docs/memory` → `docs/adr` → `docs/backlog` → `docs/specs`）
- 開発プロセス: `docs/development-workflow.md`

## Quickstart (native, Raspberry Pi / ARM first-class)

```bash
uv sync --extra dev
uv run bbc-sim generate-yaml --input config/sample_pointlist.csv --output config/simulator.yaml
uv run bbc-sim run --config config/simulator.yaml
```

## CLI

| command | 用途 |
|---------|------|
| `bbc-sim generate-yaml` | SBCO CSV → simulator.yaml |
| `bbc-sim validate` | simulator.yaml 検証 |
| `bbc-sim validate-point-list` | SBCO CSV 検証 |
| `bbc-sim run` | 仮想 B-BC 起動（BACnet/IP 北向き） |
| `bbc-sim whois` / `read-property` / `read-property-multiple` / `write-property` / `list-objects` | クライアント疎通 |

## Test

```bash
uv run pytest              # unit + loopback integration（integration マーカーは除外）
uv run pytest -m integration   # 実サービス必要（docker/compose）
uv run ruff check && uv run mypy
```
