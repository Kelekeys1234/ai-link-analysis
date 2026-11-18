"""Validation helpers for untrusted user input."""

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def validate_public_url(raw_url: str) -> str:
    """Normalize an HTTP(S) URL and reject hosts resolving to non-public IPs."""
    parts = urlsplit(raw_url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise HTTPException(status_code=422, detail="URL must use http or https and include a host")
    if parts.username or parts.password:
        raise HTTPException(status_code=422, detail="URLs containing credentials are not allowed")

    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local")):
        raise HTTPException(status_code=422, detail="Private or local network URLs are not allowed")

    try:
        addresses = {ipaddress.ip_address(host)} if _is_ip(host) else {
            ipaddress.ip_address(result[4][0])
            for result in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        }
    except (OSError, ValueError):
        raise HTTPException(status_code=422, detail="URL host could not be resolved") from None

    if not addresses or any(not address.is_global for address in addresses):
        raise HTTPException(status_code=422, detail="Private or non-public network addresses are not allowed")

    netloc = parts.netloc
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))
