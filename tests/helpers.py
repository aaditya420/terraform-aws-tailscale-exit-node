"""Reusable assertion helpers for Tailscale exit node tests."""
import socket

import requests


def is_100_range(ip: str) -> bool:
    """True if IP is in the 100.64.0.0/10 Tailscale CGNAT range."""
    parts = ip.split(".")
    return len(parts) == 4 and parts[0] == "100" and 64 <= int(parts[1]) <= 127


def is_valid_ipv4(ip: str) -> bool:
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def tailscale_api(api_key: str, method: str, path: str, **kwargs) -> requests.Response:
    """Call the Tailscale API."""
    return requests.request(
        method,
        f"https://api.tailscale.com/api/v2{path}",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        timeout=15,
        **kwargs,
    )


def get_tailscale_device(api_key: str, device_id: str) -> dict:
    resp = tailscale_api(api_key, "GET", f"/device/{device_id}?fields=all")
    resp.raise_for_status()
    return resp.json()


def get_tailscale_acl(api_key: str) -> dict:
    resp = tailscale_api(api_key, "GET", "/tailnet/-/acl")
    resp.raise_for_status()
    return resp.json()


def get_tailscale_dns(api_key: str) -> dict:
    ns = tailscale_api(api_key, "GET", "/tailnet/-/dns/nameservers")
    prefs = tailscale_api(api_key, "GET", "/tailnet/-/dns/preferences")
    ns.raise_for_status()
    prefs.raise_for_status()
    return {"nameservers": ns.json(), "preferences": prefs.json()}
