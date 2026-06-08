#!/usr/bin/env bash
# Regenerate gRPC stubs for the GatewayEgress down-link contract (ADR-017, #67).
#
# Stubs are committed under src/bbc_sim/bows/downlink/ so `uv sync --extra grpc`
# users can run `bbc-sim bows egress` without codegen. grpcio-tools lives in the
# dev group; the optional `grpc` extra provides the runtime grpcio/protobuf.
#
# Usage: ./scripts/gen_proto.sh   (run from repo root)
set -euo pipefail

OUT="src/bbc_sim/bows/downlink"

uv run --extra grpc python -m grpc_tools.protoc \
  -I proto \
  --python_out="$OUT" \
  --grpc_python_out="$OUT" \
  proto/gateway_egress.proto

# protoc emits a top-level `import gateway_egress_pb2`; rewrite it to a package-
# relative import so the stubs work when imported as bbc_sim.bows.downlink.*.
sed -i 's/^import gateway_egress_pb2/from . import gateway_egress_pb2/' \
  "$OUT/gateway_egress_pb2_grpc.py"

echo "generated: $OUT/gateway_egress_pb2.py, $OUT/gateway_egress_pb2_grpc.py"
