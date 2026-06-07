"""EP-008.6 — BOWS output conforms to the Building OS bacnet-device-message schema.

Validates against the vendored copy of the upstream schema
(`gutp-building-os-oss` DotNet/BuildingOS.Shared/Defines/Schemas/bacnet-device-message.json).
Runs in CI without a broker (PR-NF-030).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

from bbc_sim.bows.encoder import encode_device_message
from bbc_sim.bows.models import Reading
from bbc_sim.models import BacnetObjectType

SCHEMA = json.loads(
    (Path(__file__).parent / "fixtures" / "buildingos-bacnet-device-message.schema.json")
    .read_text(encoding="utf-8")
)


def test_encoder_output_validates_against_buildingos_schema():
    message = encode_device_message(
        "bbc-local-001", 1001,
        [
            Reading(BacnetObjectType.analogInput, 1001, 21.5),
            Reading(BacnetObjectType.binaryInput, 1, "active"),
            Reading(BacnetObjectType.multiStateValue, 3001, 2),
        ],
        now=datetime(2026, 6, 7, 12, 0, 0, tzinfo=UTC),
    )
    jsonschema.validate(message, SCHEMA)  # raises on non-conformance


def test_empty_device_message_validates():
    message = encode_device_message("d", 1, [], now=datetime.now(UTC))
    jsonschema.validate(message, SCHEMA)
