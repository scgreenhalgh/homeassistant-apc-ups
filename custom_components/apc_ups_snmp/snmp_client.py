"""SNMP client for APC UPS devices."""

from __future__ import annotations

import asyncio
import atexit
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# Use async pysnmp API but run it in a thread with its own event loop
# to avoid blocking the Home Assistant event loop
from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    get_cmd,
)
from pysnmp.hlapi.v3arch.asyncio import (
    usmDESPrivProtocol,
    usmAesCfb128Protocol,
    usmAesCfb192Protocol,
    usmAesCfb256Protocol,
    usm3DESEDEPrivProtocol,
    usmHMACMD5AuthProtocol,
    usmHMACSHAAuthProtocol,
    usmHMAC128SHA224AuthProtocol,
    usmHMAC192SHA256AuthProtocol,
    usmHMAC256SHA384AuthProtocol,
    usmHMAC384SHA512AuthProtocol,
)

from .const import (
    AUTH_PROTOCOL_MD5,
    AUTH_PROTOCOL_SHA,
    AUTH_PROTOCOL_SHA224,
    AUTH_PROTOCOL_SHA256,
    AUTH_PROTOCOL_SHA384,
    AUTH_PROTOCOL_SHA512,
    DEFAULT_TIMEOUT,
    PRIV_PROTOCOL_3DES,
    PRIV_PROTOCOL_AES,
    PRIV_PROTOCOL_AES192,
    PRIV_PROTOCOL_AES256,
    PRIV_PROTOCOL_DES,
    ApcOid,
)

_LOGGER = logging.getLogger(__name__)

# Thread pool executor for running SNMP operations
# Limited to 4 workers to prevent resource exhaustion
_EXECUTOR: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the thread pool executor."""
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="snmp_")
    return _EXECUTOR


def shutdown_executor() -> None:
    """Shutdown the thread pool executor.

    Called automatically at interpreter exit or can be called manually
    when the integration is unloaded.
    """
    global _EXECUTOR
    if _EXECUTOR is not None:
        _EXECUTOR.shutdown(wait=False)
        _EXECUTOR = None


# Register cleanup at interpreter exit
atexit.register(shutdown_executor)


class SnmpError(Exception):
    """Base exception for SNMP errors."""


class SnmpConnectionError(SnmpError):
    """Exception for SNMP connection errors."""


class SnmpTimeoutError(SnmpError):
    """Exception for SNMP timeout errors."""


class SnmpAuthError(SnmpError):
    """Exception for SNMP authentication errors."""


# Mapping of auth protocol names to pysnmp protocol objects
AUTH_PROTOCOL_MAP = {
    AUTH_PROTOCOL_MD5: usmHMACMD5AuthProtocol,
    AUTH_PROTOCOL_SHA: usmHMACSHAAuthProtocol,
    AUTH_PROTOCOL_SHA224: usmHMAC128SHA224AuthProtocol,
    AUTH_PROTOCOL_SHA256: usmHMAC192SHA256AuthProtocol,
    AUTH_PROTOCOL_SHA384: usmHMAC256SHA384AuthProtocol,
    AUTH_PROTOCOL_SHA512: usmHMAC384SHA512AuthProtocol,
}

# Mapping of privacy protocol names to pysnmp protocol objects
PRIV_PROTOCOL_MAP = {
    PRIV_PROTOCOL_DES: usmDESPrivProtocol,
    PRIV_PROTOCOL_3DES: usm3DESEDEPrivProtocol,
    PRIV_PROTOCOL_AES: usmAesCfb128Protocol,
    PRIV_PROTOCOL_AES192: usmAesCfb192Protocol,
    PRIV_PROTOCOL_AES256: usmAesCfb256Protocol,
}


class ApcSnmpClient:
    """SNMP client for communicating with APC UPS devices."""

    def __init__(
        self,
        host: str,
        port: int = 161,
        version: str = "v2c",
        community: str | None = None,
        username: str | None = None,
        auth_protocol: str | None = None,
        auth_password: str | None = None,
        priv_protocol: str | None = None,
        priv_password: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the SNMP client.

        Args:
            host: IP address or hostname of the UPS.
            port: SNMP port (default 161).
            version: SNMP version ("v2c" or "v3").
            community: Community string for SNMP v2c.
            username: Username for SNMP v3.
            auth_protocol: Authentication protocol for SNMP v3.
            auth_password: Authentication password for SNMP v3.
            priv_protocol: Privacy protocol for SNMP v3.
            priv_password: Privacy password for SNMP v3.
            timeout: Request timeout in seconds.
        """
        self.host = host
        self.port = port
        self.version = version
        self.community = community
        self.username = username
        self.auth_protocol = auth_protocol
        self.auth_password = auth_password
        self.priv_protocol = priv_protocol
        self.priv_password = priv_password
        self.timeout = timeout

    def _get_auth_data(self) -> CommunityData | UsmUserData:
        """Get the authentication data based on SNMP version."""
        if self.version == "v2c":
            return CommunityData(self.community or "public")

        # SNMP v3
        auth_proto = None
        priv_proto = None

        if self.auth_protocol:
            auth_proto = AUTH_PROTOCOL_MAP.get(self.auth_protocol)

        if self.priv_protocol:
            priv_proto = PRIV_PROTOCOL_MAP.get(self.priv_protocol)

        return UsmUserData(
            userName=self.username or "",
            authKey=self.auth_password,
            privKey=self.priv_password,
            authProtocol=auth_proto,
            privProtocol=priv_proto,
        )

    def _run_snmp_in_thread(self, coro_func):
        """Run an async SNMP operation in a thread with its own event loop.

        This is necessary because pysnmp does blocking I/O (file operations
        for MIB loading, DNS resolution, etc.) that would block the Home
        Assistant event loop.
        """
        def run_coro():
            return asyncio.run(coro_func())
        return run_coro

    async def _async_execute_get(self, oid: str) -> Any:
        """Execute a single SNMP GET request.

        The actual SNMP operation runs in a thread with its own event loop
        to avoid blocking the main event loop with pysnmp's file I/O.
        """
        async def do_snmp():
            try:
                engine = SnmpEngine()
                target = await UdpTransportTarget.create(
                    (self.host, self.port),
                    timeout=self.timeout,
                    retries=1,
                )

                error_indication, error_status, error_index, var_binds = await get_cmd(
                    engine,
                    self._get_auth_data(),
                    target,
                    ContextData(),
                    ObjectType(ObjectIdentity(oid)),
                )

                if error_indication:
                    error_str = str(error_indication)
                    if "timeout" in error_str.lower():
                        raise SnmpTimeoutError(f"Request timed out after {self.timeout} seconds")
                    if "unknown" in error_str.lower() or "auth" in error_str.lower():
                        raise SnmpAuthError(f"Authentication failed - check credentials: {error_str}")
                    raise SnmpConnectionError(f"Unable to connect to {self.host}:{self.port}: {error_str}")

                if error_status:
                    error_msg = error_status.prettyPrint()
                    if "authorization" in error_msg.lower() or "auth" in error_msg.lower():
                        raise SnmpAuthError(f"Authentication failed - check community string: {error_msg}")
                    # Safely get the OID that caused the error
                    error_oid = "?"
                    if error_index and var_binds and int(error_index) <= len(var_binds):
                        error_oid = str(var_binds[int(error_index) - 1][0])
                    _LOGGER.warning(
                        "SNMP error at %s: %s",
                        error_oid,
                        error_msg,
                    )
                    return None

                if var_binds:
                    _, value = var_binds[0]
                    if hasattr(value, "prettyPrint"):
                        pretty_value = value.prettyPrint()
                        if "noSuch" in pretty_value:
                            return None
                    return self._parse_value(value)

                return None

            except (SnmpConnectionError, SnmpTimeoutError, SnmpAuthError):
                raise
            except Exception as err:
                raise SnmpConnectionError(f"Unable to connect to {self.host}:{self.port}: {err}") from err

        # Run the SNMP operation in a thread with its own event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_get_executor(), self._run_snmp_in_thread(do_snmp))

    async def _async_execute_get_multiple(self, oids: list[str]) -> dict[str, Any]:
        """Execute multiple SNMP GET requests in a single operation.

        The actual SNMP operation runs in a thread with its own event loop
        to avoid blocking the main event loop with pysnmp's file I/O.
        """
        async def do_snmp():
            results: dict[str, Any] = {}

            try:
                engine = SnmpEngine()
                target = await UdpTransportTarget.create(
                    (self.host, self.port),
                    timeout=self.timeout,
                    retries=1,
                )

                object_types = [ObjectType(ObjectIdentity(oid)) for oid in oids]

                error_indication, error_status, error_index, var_binds = await get_cmd(
                    engine,
                    self._get_auth_data(),
                    target,
                    ContextData(),
                    *object_types,
                )

                if error_indication:
                    error_str = str(error_indication)
                    if "timeout" in error_str.lower():
                        raise SnmpTimeoutError(f"Request timed out after {self.timeout} seconds")
                    if "unknown" in error_str.lower() or "auth" in error_str.lower():
                        raise SnmpAuthError(f"Authentication failed: {error_str}")
                    raise SnmpConnectionError(f"Unable to connect to {self.host}:{self.port}: {error_str}")

                if error_status:
                    # Safely get the OID that caused the error
                    error_oid = "?"
                    if error_index and var_binds and int(error_index) <= len(var_binds):
                        error_oid = str(var_binds[int(error_index) - 1][0])
                    _LOGGER.warning(
                        "SNMP error at %s: %s",
                        error_oid,
                        error_status.prettyPrint(),
                    )

                for var_bind in var_binds:
                    oid_obj, value = var_bind
                    oid_str = str(oid_obj)
                    # Normalize OID format (ensure leading dot)
                    if not oid_str.startswith("."):
                        oid_str = "." + oid_str
                    results[oid_str] = self._parse_value(value)

                return results

            except (SnmpConnectionError, SnmpTimeoutError, SnmpAuthError):
                raise
            except Exception as err:
                raise SnmpConnectionError(f"Unable to connect to {self.host}:{self.port}: {err}") from err

        # Run the SNMP operation in a thread with its own event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_get_executor(), self._run_snmp_in_thread(do_snmp))

    def _parse_value(self, value: Any) -> Any:
        """Parse an SNMP value to a Python type."""
        if value is None:
            return None

        # Check for noSuchObject or noSuchInstance
        if hasattr(value, "prettyPrint"):
            pretty_value = value.prettyPrint()
            if "noSuch" in pretty_value:
                return None

        # Try to get the Python value
        if hasattr(value, "prettyPrint"):
            str_value = value.prettyPrint()

            # Try integer first
            try:
                return int(str_value)
            except ValueError:
                pass

            # Try float
            try:
                return float(str_value)
            except ValueError:
                pass

            # Return as string
            return str_value

        return value

    async def async_test_connection(self) -> bool:
        """Test the SNMP connection by querying the UPS model."""
        result = await self._async_execute_get(ApcOid.MODEL)
        return result is not None

    async def async_get(self, oid: str) -> Any:
        """Get a single OID value."""
        return await self._async_execute_get(oid)

    async def async_get_multiple(self, oids: list[str]) -> dict[str, Any]:
        """Get multiple OID values in a single request."""
        return await self._async_execute_get_multiple(oids)

    async def async_get_identity(self) -> dict[str, Any]:
        """Get UPS identity information."""
        oids = ApcOid.identity_oids()
        results = await self.async_get_multiple(oids)
        return {
            "model": results.get(ApcOid.MODEL),
            "name": results.get(ApcOid.NAME),
            "firmware": results.get(ApcOid.FIRMWARE),
            "serial": results.get(ApcOid.SERIAL),
        }

    async def async_get_all_data(self) -> dict[str, Any]:
        """Get all sensor data from the UPS."""
        all_oids = (
            ApcOid.identity_oids()
            + ApcOid.all_sensor_oids()
            + ApcOid.binary_sensor_oids()
        )
        # Remove duplicates while preserving order
        unique_oids = list(dict.fromkeys(all_oids))
        return await self.async_get_multiple(unique_oids)

    def close(self) -> None:
        """Close the SNMP engine."""
        # pysnmp doesn't require explicit cleanup
        pass
