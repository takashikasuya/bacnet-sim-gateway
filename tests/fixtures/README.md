# Test fixtures

All files in this directory are **synthetic, fictional sample data** used only by
the test suite. They do not contain any real building, device, vendor, customer,
network, or credential information.

| File | Purpose |
|------|---------|
| `sample_pointlist.csv` | Synthetic SBCO-style point list (generic placeholders: `GW001`, `DEV001`, `MainBldg`, `Room101`, `VendorA`, …) used to exercise CSV → YAML generation and object mapping. |
| `buildingos-bacnet-device-message.schema.json` | JSON Schema (draft-07) for the Building OS BACnet device-message format used in encoder tests. |

If you add fixtures, keep them fully synthetic — never copy real point lists,
addresses, or credentials into this repository.
