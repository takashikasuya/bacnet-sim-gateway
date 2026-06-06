"""Generate standards artifacts and semantic-model exports from simulator.yaml.

Implemented (PR-F-072/073): EDE CSV, IEIEJ-style object-list CSV, a PICS/BIBBs summary,
Brick/REC JSON-LD, and a WoT Thing Description. These are deterministic functions of the
config so they are snapshot-testable.

Not implemented here (MVP-3 / future, see README): BACnet/SC (PR-F-071), future objects
Schedule/TrendLog/Calendar/NotificationClass/Accumulator (PR-F-070), WoT *southbound*
binding (PR-F-086), QUDT unit ontology, and BTL certification.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from bbc_sim.models import SimulatorConfig
from bbc_sim.semantic.brick import equipment_class, point_class

# Services / BIBBs this simulator supports (EP-001..003).
SUPPORTED_SERVICES = [
    "Who-Is / I-Am",
    "ReadProperty",
    "ReadPropertyMultiple",
    "WriteProperty",
    "WritePropertyMultiple",
    "SubscribeCOV",
    "ConfirmedCOVNotification / UnconfirmedCOVNotification",
]
SUPPORTED_BIBBS = ["DS-RP-B", "DS-RPM-B", "DS-WP-B", "DS-WPM-B", "DS-COV-B", "DM-DDB-B"]


def to_ede(config: SimulatorConfig) -> str:
    """Engineering Data Exchange (EDE) CSV — the object inventory of the B-BC."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([f"# EDE export for {config.bbc.bbc_id} (device {config.bbc.device_id})"])
    w.writerow([
        "keyname", "device instance", "object-name", "object-type", "object-instance",
        "description", "present-value-default", "min-present-value", "max-present-value",
        "settable",
    ])
    for o in config.objects:
        w.writerow([
            o.point_id, config.bbc.device_id, o.object_name, o.object_type.value,
            o.object_instance, o.description, o.present_value,
            o.min_pres_value if o.min_pres_value is not None else "",
            o.max_pres_value if o.max_pres_value is not None else "",
            "Y" if o.writable else "N",
        ])
    return out.getvalue()


def to_ieiej(config: SimulatorConfig) -> str:
    """IEIEJ-style object list CSV (Japanese building-automation convention)."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["デバイスID", "オブジェクト名", "オブジェクト種別", "インスタンス番号",
                "単位", "書込可否", "説明"])
    for o in config.objects:
        w.writerow([
            config.bbc.device_id, o.object_name, o.object_type.value, o.object_instance,
            o.units or "", "可" if o.writable else "不可", o.description,
        ])
    return out.getvalue()


def to_pics(config: SimulatorConfig) -> str:
    """PICS / BIBBs summary (markdown)."""
    object_types = sorted({o.object_type.value for o in config.objects})
    lines = [
        f"# PICS — {config.bbc.bbc_id}",
        "",
        f"- Vendor: {config.bbc.vendor_name} (id {config.bbc.vendor_identifier})",
        f"- Model: {config.bbc.model_name}",
        f"- Device instance: {config.bbc.device_id}",
        "",
        "## Standardized Object Types Supported",
        *[f"- {t}" for t in object_types],
        "",
        "## BACnet Interoperability Building Blocks (BIBBs)",
        *[f"- {b}" for b in SUPPORTED_BIBBS],
        "",
        "## Services",
        *[f"- {s}" for s in SUPPORTED_SERVICES],
        "",
        "## Data Link Layer",
        "- BACnet/IP (Annex J), UDP 47808",
        "",
        "> BACnet/SC and BTL certification are out of scope (future, MVP-3).",
    ]
    return "\n".join(lines) + "\n"


def to_jsonld(config: SimulatorConfig) -> dict[str, Any]:
    """Brick/REC semantic model as JSON-LD."""
    graph: list[dict[str, Any]] = []
    device_id = f"bacnet://{config.bbc.device_id}"
    graph.append({
        "@id": device_id,
        "@type": "brick:Building_Controller",
        "rdfs:label": config.bbc.object_name,
        "brick:hasPoint": [f"{device_id}/{o.point_id}" for o in config.objects],
    })
    for o in config.objects:
        dt = str(o.metadata.get("device_type", ""))
        pt = str(o.metadata.get("point_type", ""))
        graph.append({
            "@id": f"{device_id}/{o.point_id}",
            "@type": f"brick:{point_class(pt)}",
            "rdfs:label": o.object_name,
            "brick:isPointOf": {"@type": f"brick:{equipment_class(dt)}"},
            "bacnet:object-type": o.object_type.value,
            "bacnet:object-instance": o.object_instance,
            "haystack:tags": o.tags,
        })
    return {
        "@context": {
            "brick": "https://brickschema.org/schema/Brick#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "bacnet": "http://data.ashrae.org/bacnet/#",
            "haystack": "https://project-haystack.org/def/",
        },
        "@graph": graph,
    }


def to_wot_td(config: SimulatorConfig) -> dict[str, Any]:
    """W3C WoT Thing Description for the B-BC (northbound read model)."""
    properties: dict[str, Any] = {}
    for o in config.objects:
        properties[o.point_id] = {
            "title": o.object_name,
            "type": "number" if o.object_type.is_analog else "string",
            "readOnly": not o.writable,
            "bacnet:objectType": o.object_type.value,
            "bacnet:objectInstance": o.object_instance,
            "forms": [{"href": f"bacnet://{config.bbc.device_id}/{o.object_type.value},"
                               f"{o.object_instance}/present-value"}],
        }
    return {
        "@context": ["https://www.w3.org/2019/wot/td/v1"],
        "@type": "Thing",
        "title": config.bbc.object_name,
        "id": f"urn:bbc-sim:{config.bbc.bbc_id}",
        "properties": properties,
    }


FORMATS = {
    "ede": lambda c: to_ede(c),
    "ieiej": lambda c: to_ieiej(c),
    "pics": lambda c: to_pics(c),
    "jsonld": lambda c: json.dumps(to_jsonld(c), indent=2, ensure_ascii=False),
    "wot": lambda c: json.dumps(to_wot_td(c), indent=2, ensure_ascii=False),
}


def export(config: SimulatorConfig, fmt: str) -> str:
    """Render an artifact in the given format (string)."""
    try:
        renderer = FORMATS[fmt]
    except KeyError:
        raise ValueError(f"unknown export format: {fmt!r} (choose from {sorted(FORMATS)})") \
            from None
    return renderer(config)
