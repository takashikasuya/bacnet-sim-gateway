---
name: pitfalls
description: Known failure modes and gotchas for bacnet-sim-gateway
metadata:
  type: project
---

# Pitfalls

> Add entries here when something burns time or causes a subtle bug.

## `gateway_id` を `bbc_id` に流用してはいけない（最重要）

SBCO の `gateway_id` はゲートウェイ識別子。B-BC 識別子 `bbc_id` は設定/環境変数（`BBC_ID`）で別途与える。
流用すると識別不整合・データ汚染を招く。YAML 上は `metadata.gateway_id` と `bbc.bbc_id` で別フィールド。→ [[ADR-003]]

## 連携方向を逆に実装しがち

MQTT を「北向き出力」と捉えるのは誤り。**北向き=BACnet/IP、南向き=MQTT/ZeroMQ/WoT/gRPC**。
要件定義書 v1.1 §18 の MQTT は南向きと読み替える（PRD v1.2 で訂正）。→ [[ADR-005]]

## object type 推定だけでは Output が出ない

自動推定表（[[ADR-007]]）は AI/AV/BI/BV/MI/MV のみ。Analog/Binary/Multi-state **Output** が必要なら
SBCO の BACnet 列（`object_type_bacnet`）で明示する。BACnet 列があれば推定より優先。

## BACnet/IP UDP port conflicts

Multiple BACnet stacks on the same host fight over UDP/47808.
When running tests locally alongside a real BACnet tool (e.g., YABE, BACpypes CLI),
bind the simulator to a non-default port and use BBMD/NAT routing.

## BAC0 vs bacpypes3 initialization order

_(To be documented once library is chosen — see ADR-001)_

## Docker host networking on WSL2

BACnet/IP requires UDP broadcast. Docker bridge networking blocks broadcasts by default.
Use `--network host` on Linux / WSL2 or configure a dedicated Docker bridge with `com.docker.network.bridge.host_binding_ipv4`.

## bacpypes3 0.0.106: WPM error responses don't transport over IP

`WritePropertyMultipleRequest` *success* round-trips fine, but when the server raises
`WritePropertyMultipleError` (e.g. write-access-denied on a non-writable point), the IPv4
datalink fails to send the error PDU (`NoneType has no attribute 'sendto'`) and the client
times out instead of receiving an error. This is a library limitation, not ours.
Consequence: we verify WPM write-access enforcement (AC-5) at the **handler level**
(`BBCApplication.do_WritePropertyMultipleRequest` raises the correct error) rather than
over loopback. WriteProperty (single) error responses transport correctly.

## bacpypes3 objects need a current event loop at construction

Constructing local objects schedules `_post_init` via `asyncio.ensure_future`, which needs a
current event loop. Async tests get one from pytest-asyncio; sync tests must set one (see the
`_current_loop_for_sync_tests` autouse fixture in `tests/conftest.py`). Analog objects also
need `covIncrement` set for present-value COV reporting.
