"""Reusable assertion helpers for Tailscale exit node tests."""
import base64
import io
import json as _json
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


def wait_for_bootstrap(client: paramiko.SSHClient, timeout: int = 600) -> None:
    """Block until user_data has fully completed (sentinel file exists)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc, _, _ = ssh_run(client, "test -f /tmp/bootstrap-complete")
        if rc == 0:
            return
        time.sleep(10)
    raise TimeoutError(f"Bootstrap did not complete within {timeout}s")


def ssh_run(client: paramiko.SSHClient, cmd: str) -> tuple[int, str, str]:
    """Run a command over SSH, return (exit_code, stdout, stderr)."""
    _, stdout, stderr = client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, stdout.read().decode(), stderr.read().decode()


def ssh_http_get(
    client: paramiko.SSHClient,
    path: str,
    username: str = "",
    password: str = "",
    port: int = 3000,
) -> tuple[int, dict | str]:
    """HTTP GET to AdGuard Home (localhost) via SSH. Returns (http_code, body).

    Body is a parsed dict when the response is valid JSON, otherwise a string.
    Uses Basic-auth via base64 to avoid shell-quoting issues with special chars.
    """
    auth_flag = ""
    if username:
        b64 = base64.b64encode(f"{username}:{password}".encode()).decode()
        auth_flag = f"-H 'Authorization: Basic {b64}'"

    # Write body to a temp file; capture only the status code in stdout.
    rc, code_str, _ = ssh_run(
        client,
        f"curl -s {auth_flag} -o /tmp/_agh_body -w '%{{http_code}}' "
        f"http://127.0.0.1:{port}{path}",
    )
    code = int(code_str.strip()) if code_str.strip().isdigit() else 0

    _, body_raw, _ = ssh_run(client, "cat /tmp/_agh_body 2>/dev/null")
    try:
        return code, _json.loads(body_raw)
    except Exception:
        return code, body_raw


def ssh_dns_query(
    client: paramiko.SSHClient,
    name: str,
    record_type: str = "A",
    nameserver: str = "127.0.0.1",
) -> list[str]:
    """Run dig on the remote instance, return answer records as strings."""
    rc, stdout, _ = ssh_run(client, f"dig @{nameserver} {name} {record_type} +short")
    if rc != 0:
        return []
    return [ln.strip() for ln in stdout.splitlines() if ln.strip() and not ln.startswith(";")]


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
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        timeout=15,
        **kwargs,
    )


def get_tailscale_device(api_key: str, device_id: str) -> dict:
    resp = tailscale_api(api_key, "GET", f"/device/{device_id}")
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
