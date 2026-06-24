"""Reusable assertion helpers for Tailscale exit node tests."""
import io
import re
import socket
import time

import dns.resolver
import paramiko
import requests


def wait_for_ssh(host: str, key_pem: str, timeout: int = 120) -> paramiko.SSHClient:
    """Poll until SSH is available, return connected client."""
    pkey = paramiko.RSAKey.from_private_key(io.StringIO(key_pem))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            client.connect(host, username="ubuntu", pkey=pkey, timeout=10)
            return client
        except Exception:
            time.sleep(5)
    raise TimeoutError(f"SSH to {host} did not become available within {timeout}s")


def ssh_run(client: paramiko.SSHClient, cmd: str) -> tuple[int, str, str]:
    """Run a command over SSH, return (exit_code, stdout, stderr)."""
    _, stdout, stderr = client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, stdout.read().decode(), stderr.read().decode()


def adguard_get(tailscale_ip: str, port: int, path: str, username: str, password: str) -> requests.Response:
    return requests.get(
        f"http://{tailscale_ip}:{port}{path}",
        auth=(username, password),
        timeout=10,
    )


def adguard_post(tailscale_ip: str, port: int, path: str, username: str, password: str, json=None) -> requests.Response:
    return requests.post(
        f"http://{tailscale_ip}:{port}{path}",
        auth=(username, password),
        json=json,
        timeout=10,
    )


def dns_query(nameserver: str, name: str, record_type: str = "A") -> list:
    """Query a specific nameserver and return answer records."""
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [nameserver]
    resolver.port = 53
    answers = resolver.resolve(name, record_type)
    return [str(r) for r in answers]


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
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
        **kwargs,
    )


def get_tailscale_device(api_key: str, device_id: str) -> dict:
    resp = tailscale_api(api_key, "GET", f"/device/{device_id}")
    resp.raise_for_status()
    return resp.json()


def get_tailscale_acl(api_key: str) -> dict:
    resp = tailscale_api(api_key, "GET", "/tailnet/-/acl", headers={
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    })
    resp.raise_for_status()
    return resp.json()


def get_tailscale_dns(api_key: str) -> dict:
    ns = tailscale_api(api_key, "GET", "/tailnet/-/dns/nameservers")
    prefs = tailscale_api(api_key, "GET", "/tailnet/-/dns/preferences")
    ns.raise_for_status()
    prefs.raise_for_status()
    return {"nameservers": ns.json(), "preferences": prefs.json()}
