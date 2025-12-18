# APC UPS Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/scgreenhalgh/homeassistant-apc-ups.svg)](https://github.com/scgreenhalgh/homeassistant-apc-ups/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Monitor your APC UPS devices in Home Assistant via SNMP. Get real-time battery status, power metrics, and alerts directly in your smart home dashboard.

## Features

- **SNMP v2c and v3 Support** - Secure authentication with SHA/AES encryption
- **Comprehensive Monitoring** - Battery, input/output voltage, load, runtime, and more
- **Binary Sensors** - Instant alerts for power outages and low battery
- **Multi-Device Support** - Monitor multiple UPS units from a single Home Assistant instance
- **Easy Configuration** - Simple UI-based setup wizard

## Supported Hardware

This integration works with APC UPS devices equipped with a Network Management Card (NMC):

| Network Management Card | Status |
|------------------------|--------|
| AP9630 | Tested |
| AP9631 | Should work |
| AP9635 | Should work |
| AP9640/AP9641 | Should work |

**Tested UPS Models:**
- Smart-UPS 1500

> **Note:** Any APC UPS with a Network Management Card that supports SNMP should work with this integration.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on **Integrations**
3. Click the **three dots** in the top right corner
4. Select **Custom repositories**
5. Add `https://github.com/scgreenhalgh/homeassistant-apc-ups` as an **Integration**
6. Click **Add**
7. Search for "APC UPS" and install it
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/scgreenhalgh/homeassistant-apc-ups/releases)
2. Extract and copy the `custom_components/apc_ups_snmp` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Prerequisites

Before setting up the integration, configure SNMP on your Network Management Card:

1. Log into your NMC web interface
2. Navigate to **Configuration > Network > SNMPv3**
3. Create a user profile with:
   - **Authentication**: SHA (recommended)
   - **Privacy**: AES (recommended)
   - **Access Type**: Read
4. Enable the user in **Access Control**

### Adding the Integration

1. Go to **Settings > Devices & Services**
2. Click **Add Integration**
3. Search for **APC UPS (SNMP)**
4. Enter your connection details:

| Field | Description |
|-------|-------------|
| Host | IP address of your Network Management Card |
| Port | SNMP port (default: 161) |
| SNMP Version | v2c or v3 |

5. For **SNMP v3**, enter your credentials:
   - Username
   - Authentication Protocol (SHA recommended)
   - Authentication Password
   - Privacy Protocol (AES recommended)
   - Privacy Password

6. Select the sensors you want to enable
7. Click **Submit**

## Available Sensors

### Standard Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Battery Capacity | % | Current battery charge level |
| Battery Runtime | min | Estimated time remaining on battery |
| Battery Temperature | °C | Internal battery temperature |
| Battery Voltage | V | Current battery voltage |
| Input Voltage | V | AC input voltage |
| Input Frequency | Hz | AC input frequency |
| Output Voltage | V | AC output voltage |
| Output Frequency | Hz | AC output frequency |
| Output Load | % | Current load on the UPS |
| Output Current | A | Output current draw |
| UPS Status | - | Current operating mode |

### Binary Sensors

| Sensor | Triggered When |
|--------|---------------|
| On Battery | UPS is running on battery power |
| Low Battery | Battery level is critically low |
| Replace Battery | Battery needs replacement |

## Example Dashboard Card

```yaml
type: entities
title: Server Room UPS
entities:
  - entity: sensor.ups_server_room_battery_capacity
  - entity: sensor.ups_server_room_battery_runtime
  - entity: sensor.ups_server_room_output_load
  - entity: binary_sensor.ups_server_room_on_battery
  - entity: sensor.ups_server_room_ups_status
```

## Automations

### Power Outage Notification

```yaml
automation:
  - alias: "UPS Power Outage Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.ups_server_room_on_battery
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Power Outage!"
          message: "UPS is running on battery. Runtime: {{ states('sensor.ups_server_room_battery_runtime') }} minutes"
```

### Low Battery Warning

```yaml
automation:
  - alias: "UPS Low Battery Warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ups_server_room_battery_capacity
        below: 30
    action:
      - service: notify.mobile_app
        data:
          title: "UPS Battery Low"
          message: "Battery at {{ states('sensor.ups_server_room_battery_capacity') }}%"
```

## Troubleshooting

### Cannot Connect to UPS

1. Verify the NMC is reachable: `ping <UPS_IP>`
2. Check SNMP is enabled on the NMC
3. Verify your SNMP credentials
4. Ensure port 161 is not blocked by a firewall

### Sensors Show "Unknown" or "Unavailable"

1. Check the coordinator is receiving data (enable debug logging)
2. Verify the UPS supports the OIDs being queried
3. Some older NMC firmware may not support all OIDs

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.apc_ups_snmp: debug
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built using the [pysnmp](https://github.com/lextudio/pysnmp) library
- Inspired by the Home Assistant NUT integration
