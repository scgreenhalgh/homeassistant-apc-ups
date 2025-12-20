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

**Display:**
- All numeric values show 1 decimal place (e.g., 100.0%, 24.0V)
- Uses `suggested_display_precision=1` and `to_one_decimal()` value function

### SNMP OIDs

Key OIDs are defined in `const.py` under the `ApcOid` class.

**New OIDs added in v1.0.7:**
- `TIME_ON_BATTERY`: `.1.3.6.1.4.1.318.1.1.1.2.1.2.0`
- `LAST_TRANSFER_CAUSE`: `.1.3.6.1.4.1.318.1.1.1.3.2.5.0`
- `OUTPUT_POWER`: `.1.3.6.1.4.1.318.1.1.1.4.2.8.0`

## Running Tests

```bash
python -m pytest tests/ -v
```

All 40 tests should pass.

## Common Issues

1. **HACS not showing updates**: Check you're pushing to the PUBLIC repo (`scgreenhalgh/homeassistant-apc-ups`)
2. **Blocking I/O errors**: All SNMP calls run in ThreadPoolExecutor with own event loop
3. **Config flow schema errors**: Use SelectSelector, not raw voluptuous lists
4. **Decimal places not showing**: HA UI may truncate `.0` - check Developer Tools → States for actual value
5. **New sensors not appearing**: Remove and re-add integration, or configure via Options flow

## Version History

- **v1.0.8**: Added hacs.json for HACS update tracking
- **v1.0.7**: New sensors (Last Transfer Cause, Time On Battery, Output Power), configurable polling, decimal precision
- **v1.0.6**: Code quality fixes (memory leak, deprecated API, input validation)
- **v1.0.5**: Fix blocking I/O and config flow schema serialization
