"""Tests for the APC UPS SNMP client."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.apc_ups_snmp.snmp_client import (
    ApcSnmpClient,
    SnmpAuthError,
    SnmpConnectionError,
    SnmpTimeoutError,
)


class TestSnmpClientV2c:
    """Test SNMP v2c client functionality."""

    @pytest.fixture
    def client_v2c(self) -> ApcSnmpClient:
        """Create an SNMP v2c client."""
        return ApcSnmpClient(
            host="192.168.1.100",
            port=161,
            version="v2c",
            community="public",
        )

    async def test_client_initialization_v2c(self, client_v2c: ApcSnmpClient) -> None:
        """Test SNMP v2c client initializes correctly."""
        assert client_v2c.host == "192.168.1.100"
        assert client_v2c.port == 161
        assert client_v2c.version == "v2c"
        assert client_v2c.community == "public"

    async def test_connection_success_v2c(
        self, client_v2c: ApcSnmpClient, mock_snmp_response: dict[str, Any]
    ) -> None:
        """Test successful SNMP v2c connection."""
        with patch.object(
            client_v2c, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_snmp_response[
                ".1.3.6.1.4.1.318.1.1.1.1.1.1.0"
            ]
            result = await client_v2c.async_test_connection()
            assert result is True

    async def test_connection_timeout_v2c(self, client_v2c: ApcSnmpClient) -> None:
        """Test SNMP v2c connection timeout handling."""
        with patch.object(
            client_v2c, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = SnmpTimeoutError("Connection timed out")
            with pytest.raises(SnmpTimeoutError):
                await client_v2c.async_test_connection()

    async def test_connection_auth_failure_v2c(
        self, client_v2c: ApcSnmpClient
    ) -> None:
        """Test SNMP v2c authentication failure (wrong community string)."""
        with patch.object(
            client_v2c, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = SnmpAuthError("Authentication failed")
            with pytest.raises(SnmpAuthError):
                await client_v2c.async_test_connection()

    async def test_get_single_oid_v2c(
        self, client_v2c: ApcSnmpClient, mock_snmp_response: dict[str, Any]
    ) -> None:
        """Test getting a single OID value."""
        oid = ".1.3.6.1.4.1.318.1.1.1.2.2.1.0"  # Battery capacity
        with patch.object(
            client_v2c, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_snmp_response[oid]
            result = await client_v2c.async_get(oid)
            assert result == 100  # 100% battery

    async def test_get_multiple_oids_v2c(
        self, client_v2c: ApcSnmpClient, mock_snmp_response: dict[str, Any]
    ) -> None:
        """Test getting multiple OID values in a single call."""
        oids = [
            ".1.3.6.1.4.1.318.1.1.1.2.2.1.0",  # Battery capacity
            ".1.3.6.1.4.1.318.1.1.1.4.2.3.0",  # Output load
        ]
        with patch.object(
            client_v2c, "_async_execute_get_multiple", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                oids[0]: mock_snmp_response[oids[0]],
                oids[1]: mock_snmp_response[oids[1]],
            }
            result = await client_v2c.async_get_multiple(oids)
            assert result[oids[0]] == 100
            assert result[oids[1]] == 25

    async def test_unreachable_host_v2c(self, client_v2c: ApcSnmpClient) -> None:
        """Test handling unreachable host."""
        with patch.object(
            client_v2c, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = SnmpConnectionError("Host unreachable")
            with pytest.raises(SnmpConnectionError):
                await client_v2c.async_get(".1.3.6.1.4.1.318.1.1.1.1.1.1.0")


class TestSnmpClientV3:
    """Test SNMP v3 client functionality."""

    @pytest.fixture
    def client_v3(self) -> ApcSnmpClient:
        """Create an SNMP v3 client."""
        return ApcSnmpClient(
            host="192.168.1.100",
            port=161,
            version="v3",
            username="admin",
            auth_protocol="SHA",
            auth_password="authpass123",
            priv_protocol="AES",
            priv_password="privpass123",
        )

    async def test_client_initialization_v3(self, client_v3: ApcSnmpClient) -> None:
        """Test SNMP v3 client initializes correctly."""
        assert client_v3.host == "192.168.1.100"
        assert client_v3.port == 161
        assert client_v3.version == "v3"
        assert client_v3.username == "admin"
        assert client_v3.auth_protocol == "SHA"
        assert client_v3.priv_protocol == "AES"

    async def test_connection_success_v3(
        self, client_v3: ApcSnmpClient, mock_snmp_response: dict[str, Any]
    ) -> None:
        """Test successful SNMP v3 connection."""
        with patch.object(
            client_v3, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_snmp_response[
                ".1.3.6.1.4.1.318.1.1.1.1.1.1.0"
            ]
            result = await client_v3.async_test_connection()
            assert result is True

    async def test_connection_auth_failure_v3(self, client_v3: ApcSnmpClient) -> None:
        """Test SNMP v3 authentication failure."""
        with patch.object(
            client_v3, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = SnmpAuthError("Authentication failed")
            with pytest.raises(SnmpAuthError):
                await client_v3.async_test_connection()

    async def test_get_single_oid_v3(
        self, client_v3: ApcSnmpClient, mock_snmp_response: dict[str, Any]
    ) -> None:
        """Test getting a single OID value with SNMP v3."""
        oid = ".1.3.6.1.4.1.318.1.1.1.2.2.1.0"  # Battery capacity
        with patch.object(
            client_v3, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_snmp_response[oid]
            result = await client_v3.async_get(oid)
            assert result == 100

    async def test_v3_no_priv_protocol(self) -> None:
        """Test SNMP v3 client with auth but no privacy (authNoPriv)."""
        client = ApcSnmpClient(
            host="192.168.1.100",
            port=161,
            version="v3",
            username="admin",
            auth_protocol="SHA",
            auth_password="authpass123",
            priv_protocol=None,
            priv_password=None,
        )
        assert client.priv_protocol is None
        assert client.priv_password is None

    async def test_v3_no_auth_protocol(self) -> None:
        """Test SNMP v3 client with no auth and no privacy (noAuthNoPriv)."""
        client = ApcSnmpClient(
            host="192.168.1.100",
            port=161,
            version="v3",
            username="admin",
            auth_protocol=None,
            auth_password=None,
            priv_protocol=None,
            priv_password=None,
        )
        assert client.auth_protocol is None
        assert client.priv_protocol is None


class TestSnmpClientDataParsing:
    """Test SNMP response data parsing."""

    @pytest.fixture
    def client(self) -> ApcSnmpClient:
        """Create an SNMP client for data parsing tests."""
        return ApcSnmpClient(
            host="192.168.1.100",
            port=161,
            version="v2c",
            community="public",
        )

    async def test_parse_integer_value(self, client: ApcSnmpClient) -> None:
        """Test parsing integer SNMP values."""
        with patch.object(
            client, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = 100
            result = await client.async_get(".1.3.6.1.4.1.318.1.1.1.2.2.1.0")
            assert isinstance(result, int)
            assert result == 100

    async def test_parse_string_value(self, client: ApcSnmpClient) -> None:
        """Test parsing string SNMP values."""
        with patch.object(
            client, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = "Smart-UPS 1500"
            result = await client.async_get(".1.3.6.1.4.1.318.1.1.1.1.1.1.0")
            assert isinstance(result, str)
            assert result == "Smart-UPS 1500"

    async def test_get_ups_identity(
        self, client: ApcSnmpClient, mock_snmp_response: dict[str, Any]
    ) -> None:
        """Test getting UPS identity information."""
        identity_oids = [
            ".1.3.6.1.4.1.318.1.1.1.1.1.1.0",  # Model
            ".1.3.6.1.4.1.318.1.1.1.1.1.2.0",  # Name
            ".1.3.6.1.4.1.318.1.1.1.1.2.1.0",  # Firmware
            ".1.3.6.1.4.1.318.1.1.1.1.2.2.0",  # Serial
        ]
        with patch.object(
            client, "_async_execute_get_multiple", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                oid: mock_snmp_response[oid] for oid in identity_oids
            }
            result = await client.async_get_multiple(identity_oids)
            assert result[identity_oids[0]] == "Smart-UPS 1500"
            assert result[identity_oids[1]] == "UPS_Server_Room"
            assert result[identity_oids[2]] == "UPS 09.3"
            assert result[identity_oids[3]] == "AS1234567890"


class TestSnmpClientErrorHandling:
    """Test SNMP client error handling."""

    @pytest.fixture
    def client(self) -> ApcSnmpClient:
        """Create an SNMP client for error handling tests."""
        return ApcSnmpClient(
            host="192.168.1.100",
            port=161,
            version="v2c",
            community="public",
        )

    async def test_timeout_error_message(self, client: ApcSnmpClient) -> None:
        """Test timeout error contains helpful message."""
        with patch.object(
            client, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = SnmpTimeoutError(
                "Request timed out after 5 seconds"
            )
            with pytest.raises(SnmpTimeoutError) as exc_info:
                await client.async_get(".1.3.6.1.4.1.318.1.1.1.1.1.1.0")
            assert "timed out" in str(exc_info.value).lower()

    async def test_connection_error_message(self, client: ApcSnmpClient) -> None:
        """Test connection error contains helpful message."""
        with patch.object(
            client, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = SnmpConnectionError(
                "Unable to connect to 192.168.1.100:161"
            )
            with pytest.raises(SnmpConnectionError) as exc_info:
                await client.async_get(".1.3.6.1.4.1.318.1.1.1.1.1.1.0")
            assert "192.168.1.100" in str(exc_info.value)

    async def test_auth_error_message(self, client: ApcSnmpClient) -> None:
        """Test authentication error contains helpful message."""
        with patch.object(
            client, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = SnmpAuthError(
                "Authentication failed - check community string"
            )
            with pytest.raises(SnmpAuthError) as exc_info:
                await client.async_get(".1.3.6.1.4.1.318.1.1.1.1.1.1.0")
            assert "authentication" in str(exc_info.value).lower()

    async def test_no_such_oid_returns_none(self, client: ApcSnmpClient) -> None:
        """Test that requesting a non-existent OID returns None."""
        with patch.object(
            client, "_async_execute_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None
            result = await client.async_get(".1.3.6.1.4.1.318.1.1.1.99.99.99.0")
            assert result is None
