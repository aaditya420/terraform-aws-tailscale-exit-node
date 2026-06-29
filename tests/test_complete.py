"""Integration tests for the complete (all-inputs-explicit) scenario."""
import boto3
import pytest

from conftest import complete_outputs
from helpers import get_tailscale_dns

pytestmark = pytest.mark.timeout(1800)


@pytest.fixture(scope="module")
def outputs(complete_outputs):
    return complete_outputs


@pytest.fixture(scope="module")
def ec2(outputs, aws_region):
    client = boto3.client("ec2", region_name=aws_region)
    resp = client.describe_instances(InstanceIds=[outputs["instance_id"]])
    return resp["Reservations"][0]["Instances"][0]


def test_instance_type_is_t4g_micro(ec2):
    assert ec2["InstanceType"] == "t4g.micro"


def test_name_prefix_in_tags(ec2):
    tags = {t["Key"]: t["Value"] for t in ec2.get("Tags", [])}
    assert tags.get("Name", "").startswith("ci-complete")


def test_custom_tags_present(ec2):
    tags = {t["Key"]: t["Value"] for t in ec2.get("Tags", [])}
    assert tags.get("Environment") == "ci"
    assert tags.get("Scenario") == "complete"


def test_root_volume_size_is_10gb(ec2):
    root = next(d for d in ec2["BlockDeviceMappings"] if d["DeviceName"] == ec2["RootDeviceName"])
    vol_id = root["Ebs"]["VolumeId"]
    ec2_client = boto3.client("ec2", region_name=ec2["Placement"]["AvailabilityZone"][:-1])
    vol = ec2_client.describe_volumes(VolumeIds=[vol_id])["Volumes"][0]
    assert vol["Size"] == 10


# ── Tailscale DNS nameservers ─────────────────────────────────────────────────

def test_tailnet_dns_nameservers_contains_exit_node(outputs, tailscale_api_key):
    dns = get_tailscale_dns(tailscale_api_key)
    assert outputs["tailscale_ip"] in dns["nameservers"].get("dns", [])
