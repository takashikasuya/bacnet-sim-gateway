---
name: bacnet-domain
description: BACnet protocol domain knowledge essential for this project
metadata:
  type: project
---

# BACnet Domain Knowledge

## Protocol Basics

- **BACnet** = Building Automation and Control networks (ASHRAE 135)
- Transport: BACnet/IP (UDP/47808), BACnet MS/TP (RS-485), BACnet Ethernet
- This project targets **BACnet/IP** only.

## Object Model

Every BACnet device exposes **objects**, each with **properties**.

| Object Type | Typical Use |
|-------------|-------------|
| Analog Input (AI) | Temperature, pressure sensors |
| Analog Output (AO) | Valve, damper actuators |
| Analog Value (AV) | Setpoints, calculations |
| Binary Input (BI) | On/Off sensor state |
| Binary Output (BO) | Relay, switch control |
| Binary Value (BV) | Internal flags |
| Schedule | Time-based automation |
| Device | Device metadata (mandatory) |

Key properties: `Object_Identifier`, `Object_Name`, `Present_Value`, `Description`, `Units`.

## Services

| Service | Direction | Description |
|---------|-----------|-------------|
| ReadProperty | Client→Server | Read a single property |
| WriteProperty | Client→Server | Write a property value |
| Who-Is / I-Am | Broadcast | Device discovery |
| SubscribeCOV | Client→Server | Change-of-value notification |
| ReadPropertyMultiple | Client→Server | Batch read |

## Simulator Scope

The simulator must respond to:
1. Who-Is (device discovery)
2. ReadProperty / ReadPropertyMultiple
3. WriteProperty (for controllable points)
4. SubscribeCOV (optional, future)
