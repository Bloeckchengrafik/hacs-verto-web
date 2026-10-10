"""Read-only client for the inverter's internal HTTP API."""

import asyncio
import json
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout
from yarl import URL

from .const import ENDPOINTS


class VertoError(Exception):
    """The inverter cannot supply a valid response."""


class VertoAuthError(VertoError):
    """This firmware requires authentication for an endpoint."""


def normalize_url(host: str) -> str:
    """Accept a host, host:port or HTTP(S) URL without credentials or paths."""
    value = host.strip()
    if "://" not in value:
        value = f"http://{value}"
    try:
        url = URL(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.host
            or url.user is not None
            or url.password is not None
            or url.path not in {"", "/"}
            or url.query_string
            or url.fragment
        ):
            raise ValueError("Enter an HTTP(S) host without a path or credentials")
        return str(url.origin())
    except (ValueError, TypeError) as err:
        raise ValueError("Invalid inverter address") from err


def validate_payload(endpoint: str, data: Any) -> None:
    """Reject error envelopes and schema mismatches, including login HTML."""
    if endpoint == "powerflow":
        if not isinstance(data, dict) or not isinstance(data.get("site"), dict):
            raise VertoError("Missing powerflow site")
        if not any(key in data["site"] for key in ("P_Grid", "P_PV", "P_Load")):
            raise VertoError("Missing powerflow measurements")
    elif endpoint == "devices":
        if not isinstance(data, list) or any(not isinstance(x, dict) for x in data):
            raise VertoError("Invalid device list")
    else:
        if not isinstance(data, dict):
            raise VertoError("Invalid component response")
        head = data.get("Head", {})
        status = head.get("Status", {}) if isinstance(head, dict) else {}
        if not isinstance(status, dict) or status.get("Code", 0) != 0:
            raise VertoError("Component API returned an error")
        body = data.get("Body")
        if not isinstance(body, dict) or not isinstance(body.get("Data"), dict):
            raise VertoError("Missing component data")
        for component in body["Data"].values():
            if not isinstance(component, dict) or not isinstance(component.get("channels"), dict):
                raise VertoError("Invalid component channels")


class VertoClient:
    """Use Home Assistant's shared session; never write device settings."""

    def __init__(self, session: ClientSession, host: str) -> None:
        self.session = session
        self.base_url = normalize_url(host)

    async def get(self, endpoint: str) -> Any:
        """Read exactly one known endpoint without following redirects."""
        try:
            async with self.session.get(
                self.base_url + ENDPOINTS[endpoint],
                timeout=ClientTimeout(total=8),
                allow_redirects=False,
            ) as response:
                if response.status in {401, 403}:
                    raise VertoAuthError(f"Authentication required for {endpoint}")
                if response.status != 200:
                    raise VertoError(f"HTTP {response.status} for {endpoint}")
                data = await response.json(content_type=None)
        except (ClientError, asyncio.TimeoutError, ValueError) as err:
            raise VertoError(f"Cannot read {endpoint}") from err
        validate_payload(endpoint, data)
        return data

    async def snapshot(self) -> tuple[dict[str, Any], dict[str, str]]:
        """Powerflow is required; optional failures clear their current values."""
        results = await asyncio.gather(
            *(self.get(key) for key in ENDPOINTS), return_exceptions=True
        )
        payloads: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for key, result in zip(ENDPOINTS, results, strict=True):
            if isinstance(result, Exception):
                if key == "powerflow":
                    raise result
                errors[key] = type(result).__name__
            else:
                payloads[key] = result
        return payloads, errors


def decode_nameplate(value: Any) -> dict[str, Any]:
    """Nameplate attributes are sometimes a JSON string."""
    if isinstance(value, dict):
        return value
    try:
        result = json.loads(value)
    except (ValueError, TypeError):
        return {}
    return result if isinstance(result, dict) else {}
