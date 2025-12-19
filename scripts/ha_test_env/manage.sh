#!/bin/bash
# Home Assistant Test Environment Management Script
#
# Usage:
#   ./manage.sh start     - Start HA test instance
#   ./manage.sh stop      - Stop HA test instance
#   ./manage.sh restart   - Restart HA test instance
#   ./manage.sh logs      - Show HA logs (follow mode)
#   ./manage.sh status    - Check if HA is running
#   ./manage.sh shell     - Open shell in HA container
#   ./manage.sh clean     - Stop and remove all data (fresh start)
#   ./manage.sh setup     - Configure the APC UPS integration via API
#   ./manage.sh test      - Run full test cycle (start, setup, verify, stop)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env file from project root if it exists
ENV_FILE="$SCRIPT_DIR/../../.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Configuration
HA_URL="http://localhost:8123"
CONTAINER_NAME="ha_test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

wait_for_ha() {
    log_info "Waiting for Home Assistant to start..."
    local max_attempts=60
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "$HA_URL/api/" > /dev/null 2>&1; then
            log_info "Home Assistant is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo ""
    log_error "Home Assistant did not start within expected time"
    return 1
}

get_auth_token() {
    # For trusted networks, we can use the API without auth
    # But for proper testing, we might need a long-lived token
    # This function can be extended to handle authentication
    echo ""
}

cmd_start() {
    log_info "Starting Home Assistant test instance..."

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    # Create custom_components directory if it doesn't exist
    mkdir -p config/custom_components

    docker compose up -d

    wait_for_ha

    log_info "Home Assistant is running at $HA_URL"
    log_info "To add the APC UPS integration, run: ./manage.sh setup"
}

cmd_stop() {
    log_info "Stopping Home Assistant test instance..."
    docker compose down
    log_info "Home Assistant stopped"
}

cmd_restart() {
    log_info "Restarting Home Assistant test instance..."
    docker compose restart
    wait_for_ha
    log_info "Home Assistant restarted"
}

cmd_logs() {
    log_info "Showing Home Assistant logs (Ctrl+C to exit)..."
    docker compose logs -f homeassistant
}

cmd_status() {
    if docker compose ps | grep -q "running"; then
        log_info "Home Assistant is running"
        docker compose ps

        # Check if API is responding
        if curl -s "$HA_URL/api/" > /dev/null 2>&1; then
            log_info "API is responding at $HA_URL"
        else
            log_warn "API is not responding yet"
        fi
    else
        log_warn "Home Assistant is not running"
    fi
}

cmd_shell() {
    log_info "Opening shell in Home Assistant container..."
    docker exec -it $CONTAINER_NAME /bin/bash
}

cmd_clean() {
    log_warn "This will remove all Home Assistant data. Are you sure? (y/N)"
    read -r response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        log_info "Stopping and cleaning up..."
        docker compose down -v 2>/dev/null || true
        rm -rf config/.storage config/home-assistant_v2.db config/home-assistant.log
        log_info "Cleanup complete. Run './manage.sh start' for a fresh instance."
    else
        log_info "Cancelled"
    fi
}

cmd_setup() {
    log_info "Setting up APC UPS SNMP integration..."

    # Check if HA is running
    if ! curl -s "$HA_URL/api/" > /dev/null 2>&1; then
        log_error "Home Assistant is not running. Start it first with: ./manage.sh start"
        exit 1
    fi

    # Check if we have credentials
    if [ -z "$UPS1_HOST" ]; then
        log_error "UPS credentials not found. Make sure .env file exists in project root."
        exit 1
    fi

    log_info "UPS Configuration:"
    log_info "  Host: $UPS1_HOST"
    log_info "  Port: ${UPS1_PORT:-161}"
    log_info "  Version: ${UPS1_SNMP_VERSION:-v3}"
    log_info "  Username: $UPS1_USERNAME"

    # Start the config flow
    log_info "Starting config flow..."

    # Step 1: Initialize the config flow
    FLOW_RESULT=$(curl -s -X POST "$HA_URL/api/config/config_entries/flow" \
        -H "Content-Type: application/json" \
        -d '{"handler": "apc_ups_snmp"}')

    FLOW_ID=$(echo "$FLOW_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('flow_id', ''))" 2>/dev/null)

    if [ -z "$FLOW_ID" ]; then
        log_error "Failed to start config flow. Response: $FLOW_RESULT"
        log_info "You may need to add the integration manually via the UI at $HA_URL"
        exit 1
    fi

    log_info "Config flow started: $FLOW_ID"

    # Step 2: Submit host configuration
    log_info "Submitting host configuration..."
    STEP1_RESULT=$(curl -s -X POST "$HA_URL/api/config/config_entries/flow/$FLOW_ID" \
        -H "Content-Type: application/json" \
        -d "{
            \"host\": \"$UPS1_HOST\",
            \"port\": ${UPS1_PORT:-161},
            \"snmp_version\": \"${UPS1_SNMP_VERSION:-v3}\"
        }")

    echo "Step 1 result: $STEP1_RESULT"

    # Check if we need to continue to auth step
    STEP_ID=$(echo "$STEP1_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('step_id', ''))" 2>/dev/null)

    if [ "$STEP_ID" = "auth_v3" ]; then
        log_info "Submitting SNMP v3 credentials..."

        STEP2_RESULT=$(curl -s -X POST "$HA_URL/api/config/config_entries/flow/$FLOW_ID" \
            -H "Content-Type: application/json" \
            -d "{
                \"username\": \"$UPS1_USERNAME\",
                \"auth_protocol\": \"$UPS1_AUTH_PROTOCOL\",
                \"auth_password\": \"$UPS1_AUTH_PASSWORD\",
                \"priv_protocol\": \"$UPS1_PRIV_PROTOCOL\",
                \"priv_password\": \"$UPS1_PRIV_PASSWORD\"
            }")

        echo "Step 2 result: $STEP2_RESULT"
    elif [ "$STEP_ID" = "auth_v2c" ]; then
        log_info "Submitting SNMP v2c credentials..."

        STEP2_RESULT=$(curl -s -X POST "$HA_URL/api/config/config_entries/flow/$FLOW_ID" \
            -H "Content-Type: application/json" \
            -d "{
                \"community\": \"${UPS1_COMMUNITY:-public}\"
            }")

        echo "Step 2 result: $STEP2_RESULT"
    fi

    # Check final result
    RESULT_TYPE=$(echo "${STEP2_RESULT:-$STEP1_RESULT}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type', ''))" 2>/dev/null)

    if [ "$RESULT_TYPE" = "create_entry" ]; then
        log_info "Integration configured successfully!"
        log_info "Check the Home Assistant UI at $HA_URL to see the UPS sensors."
    else
        log_error "Integration setup may have failed. Check the result above."
        log_info "You can also try adding the integration manually via the UI at $HA_URL"
    fi
}

cmd_test() {
    log_info "Running full test cycle..."

    # Start HA
    cmd_start

    # Wait a bit for everything to initialize
    sleep 5

    # Setup integration
    cmd_setup

    # Wait for data to be collected
    log_info "Waiting for sensor data to be collected..."
    sleep 30

    # Check logs for errors
    log_info "Checking logs for errors..."
    if docker compose logs homeassistant 2>&1 | grep -i "error\|exception\|blocking" | grep -i "apc_ups_snmp"; then
        log_error "Found errors in logs related to apc_ups_snmp"
        docker compose logs homeassistant 2>&1 | grep -i "apc_ups_snmp" | tail -20
    else
        log_info "No obvious errors found in logs"
    fi

    # Show recent logs
    log_info "Recent logs:"
    docker compose logs --tail=50 homeassistant 2>&1 | grep -i "apc_ups_snmp" || echo "No apc_ups_snmp logs found"

    log_info "Test cycle complete. HA is still running at $HA_URL"
    log_info "Run './manage.sh stop' to stop or './manage.sh logs' to see live logs"
}

# Main command handler
case "${1:-}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    logs)
        cmd_logs
        ;;
    status)
        cmd_status
        ;;
    shell)
        cmd_shell
        ;;
    clean)
        cmd_clean
        ;;
    setup)
        cmd_setup
        ;;
    test)
        cmd_test
        ;;
    *)
        echo "Home Assistant Test Environment Manager"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  start     Start Home Assistant test instance"
        echo "  stop      Stop Home Assistant test instance"
        echo "  restart   Restart Home Assistant test instance"
        echo "  logs      Show Home Assistant logs (follow mode)"
        echo "  status    Check if Home Assistant is running"
        echo "  shell     Open shell in Home Assistant container"
        echo "  clean     Stop and remove all data (fresh start)"
        echo "  setup     Configure the APC UPS integration via API"
        echo "  test      Run full test cycle"
        echo ""
        echo "Environment:"
        echo "  HA URL: $HA_URL"
        echo "  UPS Host: ${UPS1_HOST:-not set}"
        ;;
esac
