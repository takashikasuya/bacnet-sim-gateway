"""EP-008.2 — bacnet-device-message encoder (PR-F-101, AC-18, ADR-015)."""

from __future__ import annotations

from datetime import UTC, datetime

from bbc_sim.bows.encoder import encode_device_message
from bbc_sim.bows.models import Reading
from bbc_sim.models import BacnetObjectType

NOW = datetime(2026, 6, 7, 12, 0, 0, tzinfo=UTC)


def test_encodes_top_level_shape():
    msg = encode_device_message("bbc-local-001", 1001, [
        Reading(BacnetObjectType.analogInput, 1001, 21.5),
    ], now=NOW)
    assert isinstance(msg, list) and len(msg) == 1
    assert msg[0]["Device_id"] == "bbc-local-001"
    assert len(msg[0]["ValueString"]) == 1


def test_analog_entry_matches_schema():
    entry = encode_device_message("d", 1001, [
        Reading(BacnetObjectType.analogInput, 1001, 21.5),
    ], now=NOW)[0]["ValueString"][0]
    assert entry["TimeStamp"] == "2026-06-07T12:00:00+00:00"
    assert entry["BACnetDevice"] == 1001
    assert entry["BACnetObject"] == {
        "_base": "AnalogInput", "_value": {"ObjectType": 0, "InstanceNo": 1001}
    }
    assert entry["Properties"]["PresentValue"] == 21.5
    assert isinstance(entry["Properties"]["PresentValue"], float)


def test_object_type_enums():
    cases = {
        BacnetObjectType.analogInput: ("AnalogInput", 0),
        BacnetObjectType.analogOutput: ("AnalogOutput", 1),
        BacnetObjectType.analogValue: ("AnalogValue", 2),
        BacnetObjectType.binaryInput: ("BinaryInput", 3),
        BacnetObjectType.binaryOutput: ("BinaryOutput", 4),
        BacnetObjectType.binaryValue: ("BinaryValue", 5),
        BacnetObjectType.multiStateInput: ("MultiStateInput", 13),
        BacnetObjectType.multiStateOutput: ("MultiStateOutput", 14),
        BacnetObjectType.multiStateValue: ("MultiStateValue", 19),
    }
    for ot, (base, enum) in cases.items():
        r = Reading(ot, 1, 1)
        e = encode_device_message("d", 1, [r], now=NOW)[0]["ValueString"][0]
        assert e["BACnetObject"]["_base"] == base
        assert e["BACnetObject"]["_value"]["ObjectType"] == enum


def test_present_value_is_numeric_per_type():
    def rd(ot, v):
        return encode_device_message("d", 1, [Reading(ot, 1, v)], now=NOW)[0][
            "ValueString"][0]["Properties"]["PresentValue"]

    assert rd(BacnetObjectType.binaryInput, "active") == 1
    assert rd(BacnetObjectType.binaryInput, "inactive") == 0
    assert rd(BacnetObjectType.binaryValue, True) == 1
    assert rd(BacnetObjectType.multiStateValue, 3) == 3
    assert rd(BacnetObjectType.analogInput, 18) == 18.0


def test_reading_timestamp_overrides_now():
    ts = datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC)
    e = encode_device_message("d", 1, [
        Reading(BacnetObjectType.analogInput, 1, 1.0, timestamp=ts),
    ], now=NOW)[0]["ValueString"][0]
    assert e["TimeStamp"] == "2026-01-01T09:00:00+00:00"


def test_multiple_readings_batched_per_device():
    msg = encode_device_message("d", 1001, [
        Reading(BacnetObjectType.analogInput, 1001, 21.5),
        Reading(BacnetObjectType.binaryInput, 1, "active"),
    ], now=NOW)
    assert len(msg) == 1
    assert len(msg[0]["ValueString"]) == 2
