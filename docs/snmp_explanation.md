# SNMP - Simple Network Management Protocol

A beginner-friendly explanation for interfacing with APC UPS devices.

---

## The Basic Concept

Think of SNMP as a **standardized question-and-answer system** for network devices.

Imagine your UPS is a person who knows everything about themselves. SNMP is the language you use to ask questions:

- **You:** "What's your battery percentage?"
- **UPS:** "87%"
- **You:** "How many minutes of runtime left?"
- **UPS:** "45 minutes"

That's essentially all SNMP does - it lets you ask devices questions and get answers.

---

## Key Components

### 1. OID (Object Identifier)

This is the "address" of each piece of information. It's a string of numbers like:

```
.1.3.6.1.4.1.318.1.1.1.2.2.1
```

Each number navigates down a tree structure:

```
.1.3.6.1.4.1.318.1.1.1.2.2.1
 │ │ │ │ │ │  │  └── APC's specific data points
 │ │ │ │ │ │  └───── 318 = APC's enterprise number
 │ │ │ │ │ └──────── Private/enterprise equipment
 │ └─┴─┴─┴────────── Internet standards hierarchy
 └────────────────── ISO root
```

You don't need to memorize this - you just look up which OID corresponds to "battery percentage" in APC's documentation (called a MIB file).

### 2. MIB (Management Information Base)

This is essentially a **dictionary** that translates:

```
.1.3.6.1.4.1.318.1.1.1.2.2.1  →  "upsAdvBatteryCapacity"
```

APC publishes their MIB files so you know what questions you can ask.

### 3. Community String

This is basically a **password**. The default is often `public` for read-only access. Your UPS won't answer questions unless you provide the right community string.

---

## The Operations

SNMP really only has a few operations:

| Operation    | What it does                                         |
|--------------|------------------------------------------------------|
| **GET**      | Ask for one specific value                           |
| **GET-NEXT** | Get the next value in the tree                       |
| **WALK**     | Get ALL values under a branch (multiple GET-NEXTs)   |
| **SET**      | Change a value (if you have write access)            |
| **TRAP**     | Device proactively sends an alert (e.g., "Power failed!") |

---

## A Practical Example

Here's what querying your UPS would look like from a command line:

```bash
# Ask for battery capacity
snmpget -v2c -c public 192.168.1.100 .1.3.6.1.4.1.318.1.1.1.2.2.1.0

# Response:
# INTEGER: 100
# (meaning 100% battery)
```

Breaking that down:

- `-v2c` = Use SNMP version 2c
- `-c public` = Community string is "public"
- `192.168.1.100` = IP address of your UPS
- The OID = "What's the battery capacity?"
- `.0` at the end = Get the first (and only) instance of this value

---

## Python Example (for Home Assistant)

In Python (which Home Assistant uses), it would look something like:

```python
from pysnmp.hlapi import *

# Ask the UPS for battery capacity
iterator = getCmd(
    SnmpEngine(),
    CommunityData('public'),                            # Password
    UdpTransportTarget(('192.168.1.100', 161)),         # UPS IP, port 161
    ContextData(),
    ObjectType(ObjectIdentity('.1.3.6.1.4.1.318.1.1.1.2.2.1.0'))  # Battery %
)

errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

for varBind in varBinds:
    print(f'{varBind[0]} = {varBind[1]}')
```

---

## Summary

| Concept          | Analogy                                    |
|------------------|--------------------------------------------|
| SNMP             | A language for talking to devices          |
| OID              | The address/ID of a specific piece of data |
| MIB              | A dictionary translating OIDs to human names |
| Community String | A password                                 |
| GET              | "Tell me this value"                       |
| WALK             | "Tell me everything"                       |

---

## Common APC UPS OIDs (PowerNet-MIB)

Here are some useful OIDs for APC UPS monitoring:

| OID                                | Name                      | Description                |
|------------------------------------|---------------------------|----------------------------|
| `.1.3.6.1.4.1.318.1.1.1.1.1.1.0`   | upsBasicIdentModel        | UPS Model name             |
| `.1.3.6.1.4.1.318.1.1.1.1.1.2.0`   | upsBasicIdentName         | UPS Name                   |
| `.1.3.6.1.4.1.318.1.1.1.1.2.1.0`   | upsAdvIdentFirmwareRevision | Firmware version         |
| `.1.3.6.1.4.1.318.1.1.1.1.2.2.0`   | upsAdvIdentSerialNumber   | Serial number              |
| `.1.3.6.1.4.1.318.1.1.1.2.1.1.0`   | upsBasicBatteryStatus     | Battery status (1=unknown, 2=normal, 3=low) |
| `.1.3.6.1.4.1.318.1.1.1.2.2.1.0`   | upsAdvBatteryCapacity     | Battery capacity %         |
| `.1.3.6.1.4.1.318.1.1.1.2.2.2.0`   | upsAdvBatteryTemperature  | Battery temperature (°C)   |
| `.1.3.6.1.4.1.318.1.1.1.2.2.3.0`   | upsAdvBatteryRunTimeRemaining | Runtime remaining (timeticks) |
| `.1.3.6.1.4.1.318.1.1.1.2.2.4.0`   | upsAdvBatteryReplaceIndicator | Replace battery? (1=no, 2=yes) |
| `.1.3.6.1.4.1.318.1.1.1.3.2.1.0`   | upsAdvInputLineVoltage    | Input voltage              |
| `.1.3.6.1.4.1.318.1.1.1.3.2.4.0`   | upsAdvInputFrequency      | Input frequency (Hz)       |
| `.1.3.6.1.4.1.318.1.1.1.4.1.1.0`   | upsBasicOutputStatus      | Output status              |
| `.1.3.6.1.4.1.318.1.1.1.4.2.1.0`   | upsAdvOutputVoltage       | Output voltage             |
| `.1.3.6.1.4.1.318.1.1.1.4.2.2.0`   | upsAdvOutputFrequency     | Output frequency (Hz)      |
| `.1.3.6.1.4.1.318.1.1.1.4.2.3.0`   | upsAdvOutputLoad          | Output load %              |
| `.1.3.6.1.4.1.318.1.1.1.4.2.4.0`   | upsAdvOutputCurrent       | Output current (Amps)      |

### Output Status Values (upsBasicOutputStatus)

| Value | Meaning                    |
|-------|----------------------------|
| 1     | Unknown                    |
| 2     | Online (normal)            |
| 3     | On Battery                 |
| 4     | On Smart Boost             |
| 5     | Timed Sleeping             |
| 6     | Software Bypass            |
| 7     | Off                        |
| 8     | Rebooting                  |
| 9     | Switched Bypass            |
| 10    | Hardware Failure Bypass    |
| 11    | Sleeping Until Power Return|
| 12    | On Smart Trim              |

---

## SNMP Versions

| Version | Security                          | Notes                           |
|---------|-----------------------------------|---------------------------------|
| v1      | Community string (plaintext)      | Legacy, avoid if possible       |
| v2c     | Community string (plaintext)      | Most commonly used              |
| v3      | Username/password + encryption    | Recommended for production      |

---

## Testing Tools

### Command Line (snmpget, snmpwalk)

Install on macOS:
```bash
brew install net-snmp
```

Install on Ubuntu/Debian:
```bash
sudo apt install snmp snmp-mibs-downloader
```

### Test connectivity:
```bash
# Single value
snmpget -v2c -c public <UPS_IP> .1.3.6.1.4.1.318.1.1.1.1.1.1.0

# Walk entire APC tree
snmpwalk -v2c -c public <UPS_IP> .1.3.6.1.4.1.318.1.1.1
```

---

## Resources

- [APC PowerNet MIB Documentation](https://www.apc.com/us/en/faqs/FA156110/)
- [Net-SNMP Documentation](http://www.net-snmp.org/docs/)
- [PySNMP Documentation](https://pysnmp.readthedocs.io/)
