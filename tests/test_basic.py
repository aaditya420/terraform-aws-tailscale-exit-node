"""Integration tests for the basic (all-defaults) scenario."""
import re

import boto3
import pytest

from conftest import basic_outputs
from helpers import (
    adguard_get,
    dns_query,
    get_tailscale_acl,
    get_tailscale_device,
    get_tailscale_dns,
    is_100_range,
    is_valid_ipv4,
    ssh_run,
    wait_for_ssh,
)

pytestmark = pytest.mark.timeout(600)


@pytest.fixture(scope="module")
def outputs(basic_outputs):
    return basic_outputs


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


@pytest.fixture(scope="module")
def ts_device(outputs, tailscale_api_key):
    return get_tailscale_device(tailscale_api_key, outputs["tailscale_device_id"])


# ── EC2 resource tests ────────────────────────────────────────────────────────

def test_instance_is_running(ec2):
    assert ec2["State"]["Name"] == "running"


def test_instance_type_is_t4g_nano(ec2):
    assert ec2["InstanceType"] == "t4g.nano"


def test_instance_architecture_is_arm64(ec2):
    assert ec2["Architecture"] == "arm64"


def test_source_dest_check_disabled(ec2):
    assert ec2["SourceDestCheck"] is False


def test_root_volume_encrypted(ec2):
    root = next(d for d in ec2["BlockDeviceMappings"] if d["DeviceName"] == ec2["RootDeviceName"])
    vol_id = root["Ebs"]["VolumeId"]
    ec2_client = boto3.client("ec2", region_name=ec2["Placement"]["AvailabilityZone"][:-1])
    vol = ec2_client.describe_volumes(VolumeIds=[vol_id])["Volumes"][0]
    assert vol["Encrypted"] is True


def test_root_volume_size_is_8gb(ec2):
    root = next(d for d in ec2["BlockDeviceMappings"] if d["DeviceName"] == ec2["RootDeviceName"])
    vol_id = root["Ebs"]["VolumeId"]
    ec2_client = boto3.client("ec2", region_name=ec2["Placement"]["AvailabilityZone"][:-1])
    vol = ec2_client.describe_volumes(VolumeIds=[vol_id])["Volumes"][0]
    assert vol["Size"] == 8


def test_root_volume_type_is_gp3(ec2):
    root = next(d for d in ec2["BlockDeviceMappings"] if d["DeviceName"] == ec2["RootDeviceName"])
    vol_id = root["Ebs"]["VolumeId"]
    ec2_client = boto3.client("ec2", region_name=ec2["Placement"]["AvailabilityZone"][:-1])
    vol = ec2_client.describe_volumes(VolumeIds=[vol_id])["Volumes"][0]
    assert vol["VolumeType"] == "gp3"


def test_instance_has_name_tag(ec2):
    tags = {t["Key"]: t["Value"] for t in ec2.get("Tags", [])}
    assert tags.get("Name") == "ci-basic"


def test_ami_owner_is_canonical(ec2, aws_region):
    ec2_client = boto3.client("ec2", region_name=aws_region)
    ami = ec2_client.describe_images(ImageIds=[ec2["ImageId"]])["Images"][0]
    assert ami["OwnerId"] == "099720109477"


def test_ami_architecture_matches(ec2, aws_region):
    ec2_client = boto3.client("ec2", region_name=aws_region)
    ami = ec2_client.describe_images(ImageIds=[ec2["ImageId"]])["Images"][0]
    assert ami["Architecture"] == "arm64"


# ── Security group tests ──────────────────────────────────────────────────────

def test_sg_allows_tailscale_udp_41641(ec2, aws_region):
    sg_id = ec2["SecurityGroups"][0]["GroupId"]
    ec2_client = boto3.client("ec2", region_name=aws_region)
    sg = ec2_client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]
    udp_rules = [r for r in sg["IpPermissions"] if r.get("IpProtocol") == "udp"
                 and r.get("FromPort") == 41641]
    assert udp_rules, "No UDP 41641 ingress rule found"
    cidrs = [ip["CidrIp"] for ip in udp_rules[0].get("IpRanges", [])]
    assert "0.0.0.0/0" in cidrs


def test_sg_allows_ssh_tcp_22(ec2, aws_region):
    sg_id = ec2["SecurityGroups"][0]["GroupId"]
    ec2_client = boto3.client("ec2", region_name=aws_region)
    sg = ec2_client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]
    ssh_rules = [r for r in sg["IpPermissions"] if r.get("FromPort") == 22]
    assert ssh_rules, "No TCP 22 ingress rule found"


def test_sg_has_only_two_ingress_rules(ec2, aws_region):
    sg_id = ec2["SecurityGroups"][0]["GroupId"]
    ec2_client = boto3.client("ec2", region_name=aws_region)
    sg = ec2_client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]
    assert len(sg["IpPermissions"]) == 2


# ── Tailscale device tests ────────────────────────────────────────────────────

def test_device_is_authorized(ts_device):
    assert ts_device.get("authorized") is True


def test_device_has_correct_tag(ts_device):
    assert "tag:exit-node" in ts_device.get("tags", [])


def test_exit_node_routes_advertised(ts_device):
    advertised = ts_device.get("advertisedRoutes", [])
    assert "0.0.0.0/0" in advertised or "::/0" in advertised


def test_exit_node_routes_approved(ts_device):
    enabled = ts_device.get("enabledRoutes", [])
    assert "0.0.0.0/0" in enabled


def test_acl_has_auto_approvers(tailscale_api_key):
    acl = get_tailscale_acl(tailscale_api_key)
    auto = acl.get("autoApprovers", {})
    assert "tag:exit-node" in auto.get("exitNode", [])


def test_magic_dns_enabled(tailscale_api_key):
    dns = get_tailscale_dns(tailscale_api_key)
    assert dns["preferences"].get("magicDNS") is True


def test_tailnet_dns_nameservers_contains_exit_node(outputs, tailscale_api_key):
    dns = get_tailscale_dns(tailscale_api_key)
    assert outputs["tailscale_ip"] in dns["nameservers"].get("dns", [])


# ── AdGuard Home tests ────────────────────────────────────────────────────────

def test_adguard_process_running(ssh):
    rc, stdout, _ = ssh_run(ssh, "systemctl is-active AdGuardHome")
    assert rc == 0 and stdout.strip() == "active"


def test_adguard_port_53_listening(ssh):
    rc, stdout, _ = ssh_run(ssh, "ss -ulnp | grep ':53'")
    assert rc == 0 and "AdGuardHome" in stdout


def test_adguard_port_3000_listening(ssh):
    rc, stdout, _ = ssh_run(ssh, "ss -tlnp | grep ':3000'")
    assert rc == 0


def test_adguard_api_returns_200(outputs):
    resp = adguard_get(outputs["tailscale_ip"], 3000, "/control/status",
                       outputs["adguard_username"], outputs["adguard_password"])
    assert resp.status_code == 200


def test_adguard_wizard_completed(outputs):
    # Once wizard is done, /install/get_addresses returns 404
    resp = adguard_get(outputs["tailscale_ip"], 3000, "/install/get_addresses",
                       outputs["adguard_username"], outputs["adguard_password"])
    assert resp.status_code == 404


def test_adguard_filtering_enabled(outputs):
    resp = adguard_get(outputs["tailscale_ip"], 3000, "/control/filtering/status",
                       outputs["adguard_username"], outputs["adguard_password"])
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


def test_adguard_upstream_dns_configured(outputs):
    resp = adguard_get(outputs["tailscale_ip"], 3000, "/control/upstream_dns",
                       outputs["adguard_username"], outputs["adguard_password"])
    assert resp.status_code == 200
    upstreams = resp.json().get("upstream_dns", [])
    assert len(upstreams) > 0


def test_adguard_blocklists_loaded(outputs):
    resp = adguard_get(outputs["tailscale_ip"], 3000, "/control/filtering/status",
                       outputs["adguard_username"], outputs["adguard_password"])
    assert resp.status_code == 200
    assert len(resp.json().get("filters", [])) > 0


def test_adguard_can_resolve_legit_domain(outputs):
    records = dns_query(outputs["tailscale_ip"], "example.com", "A")
    assert len(records) > 0


def test_adguard_blocks_ad_domain(outputs):
    records = dns_query(outputs["tailscale_ip"], "doubleclick.net", "A")
    # Blocked domains resolve to 0.0.0.0 or raise NXDOMAIN
    assert records == [] or all(r == "0.0.0.0" for r in records)


# ── Output format tests ───────────────────────────────────────────────────────

def test_output_instance_public_ip_is_valid(outputs):
    assert is_valid_ipv4(outputs["instance_public_ip"])


def test_output_tailscale_ip_is_100_range(outputs):
    assert is_100_range(outputs["tailscale_ip"])


def test_output_adguard_url_format(outputs):
    assert re.match(r"^http://100\.\d+\.\d+\.\d+:\d+$", outputs["adguard_url"])


def test_output_ssh_command_format(outputs):
    assert outputs["ssh_command"].startswith("ssh -i")
