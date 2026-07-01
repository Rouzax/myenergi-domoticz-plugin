"""Manual smoke runner for the myenergi core (no Domoticz).

Usage:
    MYENERGI_SERIAL=xxxxxxxx MYENERGI_KEY=yyyy python cli_smoke.py

Prints discovered devices and today's kWh totals. Read-only.
"""

import os

from model import joules_to_kwh, parse_jday, parse_jstatus
from myenergi_client import MyEnergiClient


def main():
    serial = os.environ["MYENERGI_SERIAL"]
    key = os.environ["MYENERGI_KEY"]
    client = MyEnergiClient(serial=serial, api_key=key)
    asn = client.discover_from_director()
    print(f"ASN: {asn}")

    status = parse_jstatus(client.fetch_status())
    for dev in status.devices:
        roles = ",".join(f"{ct.index}:{ct.role}={ct.power_w}W" for ct in dev.cts)
        print(f"{dev.kind} {dev.serial}: {roles}")

    jday = client.fetch_jday("Z", serial, _today_from_status(status))
    sums = parse_jday(jday)
    for field_name in ("gep", "imp", "exp"):
        if field_name in sums:
            print(f"today {field_name}: {joules_to_kwh(sums[field_name]):.2f} kWh")


def _today_from_status(status):
    # zappi status carries dat as DD-MM-YYYY; normalise to YYYY-MM-DD for jday call.
    dat = status.zappi.get("dat", "")
    parts = dat.split("-")
    if len(parts) == 3:
        d, m, y = parts
        return f"{y}-{int(m)}-{int(d)}"
    raise SystemExit("no date in zappi status")


if __name__ == "__main__":
    main()
