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

## Docker (optional, ADR-008)

```bash
docker compose -f docker/docker-compose.yml up --build   # network_mode: host for BACnet/IP
```

## Test

```bash
uv run pytest              # unit + loopback integration（integration マーカーは除外）
uv run pytest -m integration   # 実サービス必要（docker/compose）
uv run ruff check && uv run mypy
```

## Manual acceptance (EP-001.9)

自動テストで担保できない項目（手動確認）:

- **Raspberry Pi (ARM/ARM64) ネイティブ起動**: 実機で `uv sync && uv run bbc-sim run -c config/simulator.yaml`（PR-NF-019/020, ADR-008）。CI/loopback はネイティブ起動経路を `bbc-sim run` のサブプロセス e2e で確認済みだが、ARM 実機確認は手動。
- **YABE 北向き接続**: 同一サブネットの YABE から仮想 B-BC を探索し、ReadProperty/WriteProperty を GUI で確認（TS-02..05 の GUI 経路）。プロトコル往復はループバック統合テストで確認済み。
