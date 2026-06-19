#!/usr/bin/env bash
# Regenerate gRPC stubs for GatewayEgress (down-link) and GatewayIngress (up-link).
#
# Stubs are committed so `uv sync --extra grpc` users can run connectors without codegen.
# grpcio-tools lives in the dev group; the optional `grpc` extra provides the runtime.
#
# Usage: ./scripts/gen_proto.sh   (run from repo root)
set -euo pipefail

EGRESS_OUT="src/bbc_sim/bows/downlink"
INGRESS_OUT="src/bbc_sim/bows/uplink"

# --- egress ---
uv run --extra grpc python -m grpc_tools.protoc \
  -I proto \
  --python_out="$EGRESS_OUT" \
  --grpc_python_out="$EGRESS_OUT" \
  proto/gateway_egress.proto

sed -i.bak 's/^import gateway_egress_pb2/from . import gateway_egress_pb2/' \
  "$EGRESS_OUT/gateway_egress_pb2_grpc.py"
rm -f "$EGRESS_OUT/gateway_egress_pb2_grpc.py.bak"

# --- ingress ---
uv run --extra grpc python -m grpc_tools.protoc \
  -I proto \
  --python_out="$INGRESS_OUT" \
  --grpc_python_out="$INGRESS_OUT" \
  proto/gateway_ingress.proto

sed -i.bak 's/^import gateway_ingress_pb2/from . import gateway_ingress_pb2/' \
  "$INGRESS_OUT/gateway_ingress_pb2_grpc.py"
rm -f "$INGRESS_OUT/gateway_ingress_pb2_grpc.py.bak"

echo "generated:"
echo "  $EGRESS_OUT/gateway_egress_pb2.py, $EGRESS_OUT/gateway_egress_pb2_grpc.py"
echo "  $INGRESS_OUT/gateway_ingress_pb2.py, $INGRESS_OUT/gateway_ingress_pb2_grpc.py"
