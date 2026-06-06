"""Southbound binding: protocol-independent telemetry/command wiring (ADR-005, ADR-013).

Northbound is always BACnet/IP; southbound (MQTT/ZeroMQ/WoT/gRPC) is the data source in
gateway/combined modes. This package is transport-agnostic: the binding logic talks to a
``Transport`` protocol, with an in-memory transport for self-contained tests.
"""
