"""Integration tests for the no-AdGuard (plain exit node) scenario."""
import boto3
import pytest

from conftest import no_adguard_outputs
from helpers import get_tailscale_dns

pytestmark = pytest.mark.timeout(1800)


@pytest.fixture(scope="module")
def outputs(no_adguard_outputs):
    return no_adguard_outputs


@pytest.fixture(scope="module")
def ec2(outputs, aws_region):
    client = boto3.client("ec2", region_name=aws_region)
    resp = client.describe_instances(InstanceIds=[outputs["instance_id"]])
    return resp["Reservations"][0]["Instances"][0]


def test_instance_is_running(ec2):
    assert ec2["State"]["Name"] == "running"


def test_adguard_url_output_is_empty(outputs):
    assert outputs.get("adguard_url", "") == ""


def test_tailnet_dns_not_set_to_exit_node(outputs, tailscale_api_key):
    dns = get_tailscale_dns(tailscale_api_key)
    nameservers = dns["nameservers"].get("dns", [])
    assert outputs.get("tailscale_ip") not in nameservers
