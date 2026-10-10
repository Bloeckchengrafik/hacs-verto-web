# Fronius Verto Web

> [!note]
> This is 100% vibecoded.
> The only reason this is a public project is to make HACS integration easier

Read-only Home Assistant custom integration for the **local Verto web interface API**.
Works with Solar API disabled. No Modbus connection, Solar.web account or cloud service is used.

## Installation

For a public repository: HACS → three dots → Custom repositories → add
`https://github.com/Bloeckchengrafik/hacs-verto-web`, category **Integration**.
Download **Fronius Verto Web**, restart Home Assistant, then add it under
**Settings → Devices & services → Add integration**.

If this repository is private, use manual installation: download the repository
while signed into GitHub and copy `custom_components/verto_web` into
`/config/custom_components/verto_web`. Restart Home Assistant and add the integration.

Enter the **inverter's** address, for example `172.16.21.148` or
`http://172.16.21.148:80`. Do not enter the Smart Meter's address.
HTTP(S) addresses and non-default ports are supported. HTTPS needs a trusted
certificate; certificate validation is not bypassed.

Default polling is 10 seconds. Change it under the integration's options (5–300 seconds).
Home Assistant must have network access to the inverter.

## Endpoints and entities

| Endpoint | Entities |
| --- | --- |
| `/api/status/powerflow` | PV, grid, load and battery power; separate import/export and charge/discharge power; SOC per inverter; autonomy and self consumption when supplied; backup and standby flags |
| `/api/status/devices` | Raw device status messages |
| `/api/components/PowerMeter/readable` | All discovered meters: consumed/produced energy totals, active power, frequency and per-phase voltage, current and active power where supplied |
| `/api/components/BatteryManagementSystem/readable` | All discovered batteries: SOC, SOH, DC current/voltage, temperatures, charge/discharge energy totals and capacities where supplied |

The integration requires a valid powerflow response. Other endpoints are optional:
failures make their entities unavailable while powerflow keeps updating. Later
appearing devices and channels are discovered automatically. Missing or null
measurements never become artificial zero readings. One poll fetches each endpoint
once, independently of the number of enabled entities.

Unknown numeric/string component channels are diagnostic sensors, **disabled by
default**, with their original channel names and no assumed units or statistics.
Enable individual sensors from the device's entities list if useful. Diagnostics
include channel names and endpoint failures, but not serial numbers, raw attributes,
IP addresses or device identifiers.

## Signs and energy units

| Reading | Convention |
| --- | --- |
| Grid power (`site.P_Grid`) | Positive = import; negative = export |
| Battery power (`site.P_Akku`) | Positive = discharge; negative = charge |
| Load power | Negated `site.P_Load`, normally positive consumption |
| Meter consumed/produced energy | API Wh divided by 1,000 → kWh |
| Battery lifetime energies and capacities | API Ws divided by 3,600,000 → kWh |
| Nameplate capacity | Nameplate Wh divided by 1,000 → kWh |
| Inverter AC energy total | Powerflow `E_Total` Wh divided by 1,000 → kWh; disabled by default |

Meter totals are suitable for the HA Energy dashboard **when the meter is at the
grid connection**: consumed → grid import; produced → grid export. For meters in
other locations those readings describe that meter, not necessarily grid exchange.
Battery charge/discharge counters can be selected under battery storage. Compare
the counters against the inverter UI on first use, particularly on newer firmware.

On hybrid systems, inverter **AC energy total includes battery output** and should
not be treated as a pure solar-generation counter. For solar energy, use Home
Assistant's Integral helper on **PV power** (W → kWh with kilo prefix and hours).
The integration does not manufacture daily/yearly counters when the API returns null.

## Firmware and authentication

This is an **internal API**: the supplied response explicitly says it may change
at any time. Firmware can change channel names or endpoint accessibility.
The initial implementation is based on supplied Verto powerflow/device/Reserva
battery responses and independently observed GEN24 meter channel names. **Live
Smart Meter IP data and installation on the physical Verto still need validation.**

Requests are ordinary unauthenticated GETs. If a firmware version requires login,
setup reports that fact; this integration does not bypass authentication or reuse
browser cookies. It exposes monitoring sensors, not inverter/battery configuration
controls. The inverter's own internal Modbus links mentioned in attributes are
unrelated to how this integration communicates with it.

Channel-unit references:
- Meter Wh mapping: [PyFronius](https://github.com/nielstron/pyfronius/blob/master/pyfronius/__init__.py).
- Battery Ws conversion: [energy counter client](https://github.com/snejrelhceuk-arch/fronius-pv-monitoring/blob/main/scripts/check_energy_counters.py).
- Meter payload shape: [recorded PowerMeter response](https://github.com/teknoid/dac/blob/master/www/pv/components/PowerMeter/readable).

## Development

Python 3.13; tests use Home Assistant 2026.2.3.

```sh
pip install homeassistant==2026.2.3 pytest pytest-asyncio pytest-aiohttp ruff
pytest -q
ruff check .
ruff format --check .
```

Tests cover sanitized supplied values, power signs, different energy units,
missing measurements, multiple meters, optional-endpoint failures, auth errors,
HTML/redirect rejection, cancellation, HA entity metadata, availability and late discovery.
GitHub Actions also runs hassfest.
