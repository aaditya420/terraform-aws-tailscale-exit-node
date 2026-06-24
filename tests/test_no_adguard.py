"""Integration tests for the no-AdGuard (plain exit node) scenario."""
import pytest
import requests

from conftest import no_adguard_outputs
from helpers import get_tailscale_dns, ssh_run, wait_for_ssh

pytestmark = pytest.mark.timeout(600)


@pytest.fixture(scope="module")
def outputs(no_adguard_outputs):
    return no_adguard_outputs


@pytest.fixture(scope="module")
def ssh(outputs):
    client = wait_for_ssh(outputs["instance_public_ip"], outputs["private_key_pem"])
    yield client
    client.close()


def test_adguard_process_not_running(ssh):
    rc, _, _ = ssh_run(ssh, "systemctl is-active AdGuardHome")
    assert rc != 0


def test_port_53_not_bound_to_adguard(ssh):
    _, stdout, _ = ssh_run(ssh, "ss -ulnp | grep ':53'")
    assert "AdGuardHome" not in stdout


def test_port_3000_not_listening(ssh):
    rc, _, _ = ssh_run(ssh, "ss -tlnp | grep ':3000'")
    assert rc != 0


def test_adguard_url_output_is_empty(outputs):
    assert outputs.get("adguard_url", "") == ""


def test_tailnet_dns_not_set_to_exit_node(outputs, tailscale_api_key):
    dns = get_tailscale_dns(tailscale_api_key)
    nameservers = dns["nameservers"].get("dns", [])
    assert outputs.get("tailscale_ip") not in nameservers


def test_basic_internet_dns_works(ssh):
    rc, stdout, _ = ssh_run(ssh, "dig +short @8.8.8.8 example.com A")
    assert rc == 0 and stdout.strip()
