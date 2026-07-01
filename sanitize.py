"""Security-critical input validation: label/serial sanitizing and ASN allowlist."""
import re

_LABEL_ALLOWED = re.compile(r"[^A-Za-z0-9 _.:+/-]")
_ASN_RE = re.compile(r"^[a-z0-9.-]+\.myenergi\.net\Z")


def clean_label(s: str, max_len: int = 64) -> str:
    s = str(s).replace("\n", "").replace("\r", "").replace("\t", "")
    s = _LABEL_ALLOWED.sub("", s)
    return s[:max_len]


def clean_serial(s) -> "str | None":
    s = str(s).strip()
    return s if s.isdigit() else None


def validate_asn_host(host: object) -> "str | None":
    if not isinstance(host, str):
        return None
    host = host.strip().lower()
    if "/" in host or "@" in host or ":" in host or " " in host:
        return None
    if not _ASN_RE.match(host):
        return None
    return host
