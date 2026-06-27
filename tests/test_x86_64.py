"""Integration tests for the x86_64 architecture scenario."""
import boto3
import pytest

from conftest import x86_outputs
from helpers import (
    ssh_dns_query,
    ssh_http_get,
    wait_for_bootstrap,
    wait_for_ssh,
)

pytestmark = pytest.mark.timeout(1800)


@pytest.fixture(scope="module")
def outputs(x86_outputs):
    return x86_outputs


@pytest.fixture(scope="module")
def ec2(outputs, aws_region):
    client = boto3.client("ec2", region_name=aws_region)
    resp = client.describe_instances(InstanceIds=[outputs["instance_id"]])
    return resp["Reservations"][0]["Instances"][0]


@pytest.fixture(scope="module")
def ssh(outputs):
    client = wait_for_ssh(outputs["instance_public_ip"], outputs["private_key_pem"])
    wait_for_bootstrap(client)
    yield client
    client.close()


def test_instance_type_is_t3_micro(ec2):
    assert ec2["InstanceType"] == "t3.micro"


def test_instance_architecture_is_x86_64(ec2):
    assert ec2["Architecture"] == "x86_64"


def test_ami_architecture_is_x86_64(ec2, aws_region):
    ec2_client = boto3.client("ec2", region_name=aws_region)
    ami = ec2_client.describe_images(ImageIds=[ec2["ImageId"]])["Images"][0]
    assert ami["Architecture"] == "x86_64"


def test_tailscale_and_adguard_functional(ssh, outputs):
    code, _ = ssh_http_get(ssh, "/control/status",
                           outputs["adguard_username"], outputs["adguard_password"])
    assert code == 200


def test_dns_resolves_on_x86_node(ssh):
    records = ssh_dns_query(ssh, "example.com", "A")
    assert len(records) > 0
