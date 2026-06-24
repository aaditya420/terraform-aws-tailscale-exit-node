"""Integration tests for the complete (all-inputs-explicit) scenario."""
import boto3
import pytest

from conftest import complete_outputs
from helpers import adguard_get, ssh_run, wait_for_ssh

pytestmark = pytest.mark.timeout(600)


@pytest.fixture(scope="module")
def outputs(complete_outputs):
    return complete_outputs


@pytest.fixture(scope="module")
def ec2(outputs, aws_region):
    client = boto3.client("ec2", region_name=aws_region)
    resp = client.describe_instances(InstanceIds=[outputs["instance_id"]])
    return resp["Reservations"][0]["Instances"][0]


@pytest.fixture(scope="module")
def ssh(outputs):
    client = wait_for_ssh(outputs["instance_public_ip"], outputs["private_key_pem"])
    yield client
    client.close()


def test_instance_type_is_t4g_micro(ec2):
    assert ec2["InstanceType"] == "t4g.micro"


def test_name_prefix_in_tags(ec2):
    tags = {t["Key"]: t["Value"] for t in ec2.get("Tags", [])}
    assert tags.get("Name") == "ci-complete"


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


def test_explicit_adguard_credentials_work(outputs):
    resp = adguard_get(outputs["tailscale_ip"], 3000, "/control/status",
                       "testadmin", "CiT3stP@ss!")
    assert resp.status_code == 200


def test_adguard_pinned_version_installed(ssh):
    rc, stdout, _ = ssh_run(ssh, "/opt/AdGuardHome/AdGuardHome --version")
    assert rc == 0 and "v0.107.77" in stdout


def test_adguard_custom_upstream_dns_only(outputs):
    resp = adguard_get(outputs["tailscale_ip"], 3000, "/control/upstream_dns",
                       "testadmin", "CiT3stP@ss!")
    upstreams = resp.json().get("upstream_dns", [])
    assert any("quad9" in u for u in upstreams)
    assert not any("cloudflare" in u for u in upstreams)


def test_adguard_custom_blocklist_present(outputs):
    resp = adguard_get(outputs["tailscale_ip"], 3000, "/control/filtering/status",
                       "testadmin", "CiT3stP@ss!")
    urls = [f["url"] for f in resp.json().get("filters", [])]
    assert any("filter_1" in u for u in urls)
