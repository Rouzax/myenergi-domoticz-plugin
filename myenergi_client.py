"""myenergi cloud transport: digest auth, ASN allowlist, host-scoped credentials.

Read-only in Plan 1. Never logs the API key or Authorization header; never enables
transport debuglevel; HTTPS + verified TLS only (stdlib default context).
"""

import json
import urllib.request

from sanitize import validate_asn_host

DIRECTOR_URL = "https://director.myenergi.net"


class AsnValidationError(Exception):
    pass


class MyEnergiClient:
    def __init__(self, serial, api_key, opener_factory=None, max_bytes=1_048_576):
        self._serial = serial
        self._api_key = api_key
        self._max_bytes = max_bytes
        self._asn = None
        # Digest credentials scoped to *.myenergi.net so urllib will not emit
        # Authorization to any other host even if a redirect slips through.
        # HTTPPasswordMgrWithDefaultRealm is required so find_user_password falls
        # back to the realm=None entry when the server presents its own realm string
        # (e.g. "MyEnergi Telemetry") that was not registered explicitly.
        pwmgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        for host in ("director.myenergi.net", "myenergi.net"):
            pwmgr.add_password(realm=None, uri=f"https://{host}", user=serial, passwd=api_key)
        self._pwmgr = pwmgr
        self._opener_factory = opener_factory or self._default_opener

    def _default_opener(self):
        handler = urllib.request.HTTPDigestAuthHandler(self._pwmgr)
        return urllib.request.build_opener(handler)

    def __repr__(self):
        return f"MyEnergiClient(serial={self._serial!r})"

    @property
    def base_url(self):
        return f"https://{self._asn}" if self._asn else None

    def discover_asn(self, headers) -> str:
        raw = None
        for key, val in dict(headers).items():
            if key.lower() == "x_myenergi-asn":
                raw = val
                break
        host = validate_asn_host(raw) if raw is not None else None
        if host is None:
            raise AsnValidationError(f"invalid or missing X_MYENERGI-asn: {raw!r}")
        self._asn = host
        # Register credentials for the discovered ASN host so urllib's digest handler
        # matches this specific subdomain. URI matching does not treat myenergi.net as
        # covering s18.myenergi.net; each subdomain needs its own entry.
        # validate_asn_host already confirmed host matches *.myenergi.net.
        self._pwmgr.add_password(None, f"https://{host}", self._serial, self._api_key)
        return host

    def _get_json(self, url):
        opener = self._opener_factory()
        req = urllib.request.Request(url, headers={"User-Agent": "Domoticz-myenergi"})
        with opener.open(req, timeout=15) as resp:
            body = resp.read(self._max_bytes)
        return json.loads(body.decode("utf-8"))

    def fetch_status(self):
        if not self.base_url:
            raise RuntimeError("ASN not discovered yet; call discover_from_director first")
        return self._get_json(f"{self.base_url}/cgi-jstatus-*")

    def fetch_jday(self, device_letter, serial, iso_date):
        y, m, d = (int(p) for p in iso_date.split("-"))
        return self._get_json(f"{self.base_url}/cgi-jday-{device_letter}{serial}-{y}-{m}-{d}")

    def discover_from_director(self):
        opener = self._opener_factory()
        req = urllib.request.Request(
            f"{DIRECTOR_URL}/cgi-jstatus-E", headers={"User-Agent": "Domoticz-myenergi"}
        )
        with opener.open(req, timeout=15) as resp:
            return self.discover_asn(dict(resp.headers))
