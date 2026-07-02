"""myenergi cloud transport: digest auth, ASN allowlist, host-scoped credentials.

Read methods (`fetch_status`, `fetch_jday`, `discover_from_director`) are always
available. Write methods (zappi mode, boost, min-green, lock) are gated off by
default and only run when `writes_enabled` / `lock_enabled` is explicitly set.
Never logs the API key or Authorization header; never enables transport
debuglevel; HTTPS + verified TLS only (stdlib default context).
"""

import json
import urllib.request

from sanitize import validate_asn_host

DIRECTOR_URL = "https://director.myenergi.net"


class AsnValidationError(Exception):
    pass


class WriteError(Exception):
    pass


class MyEnergiClient:
    def __init__(
        self,
        serial,
        api_key,
        opener_factory=None,
        max_bytes=1_048_576,
        writes_enabled=False,
        lock_enabled=False,
        control_timeout=5,
    ):
        self._serial = serial
        self._api_key = api_key
        self._max_bytes = max_bytes
        self._asn = None
        self._writes_enabled = writes_enabled
        self._lock_enabled = lock_enabled
        self._control_timeout = control_timeout
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

    def _get_json(self, url, timeout=15):
        opener = self._opener_factory()
        req = urllib.request.Request(url, headers={"User-Agent": "Domoticz-myenergi"})
        with opener.open(req, timeout=timeout) as resp:
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

    def _control_get(self, serial, path, allow):
        if not allow:
            raise WriteError("control writes disabled")
        if not str(serial).isdigit():
            raise WriteError("invalid serial")
        if not self.base_url:
            raise WriteError("ASN not discovered yet")
        return self._get_json(f"{self.base_url}{path}", timeout=self._control_timeout)

    def set_zappi_mode(self, serial, mode):
        path = f"/cgi-zappi-mode-Z{serial}-{int(mode)}-0-0-0000"
        return self._control_get(serial, path, self._writes_enabled)

    def set_boost_manual(self, serial, kwh):
        path = f"/cgi-zappi-mode-Z{serial}-0-10-{int(kwh)}-0000"
        return self._control_get(serial, path, self._writes_enabled)

    def set_boost_smart(self, serial, kwh, hhmm):
        path = f"/cgi-zappi-mode-Z{serial}-0-11-{int(kwh)}-{hhmm}"
        return self._control_get(serial, path, self._writes_enabled)

    def cancel_boost(self, serial):
        path = f"/cgi-zappi-mode-Z{serial}-0-2-0-0000"
        return self._control_get(serial, path, self._writes_enabled)

    def set_min_green(self, serial, pct):
        path = f"/cgi-set-min-green-Z{serial}-{int(pct)}"
        return self._control_get(serial, path, self._writes_enabled)

    def set_lock(self, serial, bitmask):
        path = f"/cgi-jlock-{serial}-{bitmask}"
        return self._control_get(serial, path, self._lock_enabled)
