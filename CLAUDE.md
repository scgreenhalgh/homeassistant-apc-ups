# APC UPS SNMP Integration - Project Notes

## Repository Setup

**IMPORTANT: This project uses TWO repositories!**

| Repository | URL | Visibility | Purpose |
|------------|-----|------------|---------|
| **Development** | `scgreenhalgh/ha_apc_ups_dev` | Private | Development & testing |
| **Public/HACS** | `scgreenhalgh/homeassistant-apc-ups` | Public | HACS distribution |

### Git Remotes

```bash
origin  -> ha_apc_ups_dev (private)
public  -> homeassistant-apc-ups (public/HACS)
```

### Release Process

When releasing a new version, you MUST push to BOTH repositories:

```bash
# 1. Push code to both repos
git push origin main
git push public main

# 2. Create release on PUBLIC repo (for HACS)
gh release create vX.Y.Z --repo scgreenhalgh/homeassistant-apc-ups --title "vX.Y.Z: Title" --notes "Release notes"

# 3. Optionally create on private repo too
gh release create vX.Y.Z --title "vX.Y.Z: Title" --notes "Release notes"
```

## Test Environment

### Docker-based Home Assistant

Location: `scripts/ha_test_env/`

```bash
./manage.sh start    # Start HA
./manage.sh stop     # Stop HA
./manage.sh restart  # Restart (use after code changes)
./manage.sh logs     # View logs
./manage.sh clean    # Fresh start
```

Access: http://localhost:8123

### Real UPS for Testing

- **Host**: 192.168.0.71
- **Port**: 161
- **SNMP Version**: v3
- Credentials in `.env` file (git-ignored)

## Integration Details

### Key Files

- `custom_components/apc_ups_snmp/` - Main integration code
- `tests/` - pytest unit tests
- `scripts/test_real_ups.py` - Direct UPS testing script
- `hacs.json` - HACS configuration

### Current Features (v1.0.8)

**Sensors:**
- Battery: Capacity, Runtime, Temperature, Voltage, Time On Battery
- Input: Voltage, Frequency, Last Transfer Cause
- Output: Voltage, Frequency, Load, Current, Power, Status

**Options:**
- Configurable polling interval (10-300 seconds, default 30s)
- Selectable sensors

### SNMP OIDs

Key OIDs are defined in `const.py` under the `ApcOid` class.

## Running Tests

```bash
python -m pytest tests/ -v
```

## Common Issues

1. **HACS not showing updates**: Check you're pushing to the PUBLIC repo
2. **Blocking I/O errors**: All SNMP calls run in ThreadPoolExecutor
3. **Config flow schema errors**: Use SelectSelector, not raw voluptuous lists
