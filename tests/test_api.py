"""Exercise the actual HTTP client against an aiohttp server."""

import asyncio

import pytest
from aiohttp import ClientSession, web

from custom_components.verto_web.api import VertoAuthError, VertoClient, VertoError, normalize_url
from custom_components.verto_web.const import ENDPOINTS


@pytest.mark.parametrize(
    "host,expected",
    [
        ("172.16.21.148", "http://172.16.21.148"),
        ("http://inverter.local:80/", "http://inverter.local"),
        ("https://inverter.local:444", "https://inverter.local:444"),
        ("http://[::1]:8801", "http://[::1]:8801"),
    ],
)
def test_url(host, expected):
    assert normalize_url(host) == expected


@pytest.mark.parametrize(
    "host",
    [
        "",
        "ftp://inverter",
        "http://u:p@inverter",
        "http://inverter/api",
        "http://inverter?x=1",
        "http://inverter:bad",
    ],
)
def test_invalid_url(host):
    with pytest.raises(ValueError):
        normalize_url(host)


async def test_http_snapshot_optional_failure(aiohttp_server, payloads):
    seen = []

    async def handler(request):
        seen.append((request.method, request.path))
        endpoint = next(key for key, path in ENDPOINTS.items() if path == request.path)
        if endpoint == "meter":
            return web.Response(status=404)
        return web.json_response(payloads[endpoint])

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    server = await aiohttp_server(app)
    async with ClientSession() as session:
        data, errors = await VertoClient(session, str(server.make_url("/"))).snapshot()
    assert "powerflow" in data and "battery" in data and "meter" not in data
    assert errors == {"meter": "VertoError"}
    assert len(seen) == 4 and all(method == "GET" for method, _ in seen)


@pytest.mark.parametrize(
    "status,body,error",
    [
        (401, "", VertoAuthError),
        (403, "", VertoAuthError),
        (302, "", VertoError),
        (500, "", VertoError),
        (200, "<html>Login</html>", VertoError),
        (200, '{"site":{}}', VertoError),
        (200, '"Disabled"', VertoError),
    ],
)
async def test_required_endpoint_errors(aiohttp_server, status, body, error):
    async def handler(request):
        return web.Response(status=status, text=body)

    app = web.Application()
    app.router.add_get("/{tail:.*}", handler)
    server = await aiohttp_server(app)
    async with ClientSession() as session:
        with pytest.raises(error):
            await VertoClient(session, str(server.make_url("/"))).snapshot()


async def test_cancellation_propagates():
    class BlockingClient(VertoClient):
        async def get(self, endpoint):
            await asyncio.Event().wait()

    task = asyncio.create_task(BlockingClient(None, "inverter.local").snapshot())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
