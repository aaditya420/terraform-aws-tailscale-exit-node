"""Integration tests for the custom VPC/subnet scenario."""
import boto3
import pytest

from conftest import custom_vpc_outputs

pytestmark = pytest.mark.timeout(1800)


@pytest.fixture(scope="module")
def outputs(custom_vpc_outputs):
    return custom_vpc_outputs


@pytest.fixture(scope="module")
def ec2(outputs, aws_region):
    client = boto3.client("ec2", region_name=aws_region)
    resp = client.describe_instances(InstanceIds=[outputs["instance_id"]])
    return resp["Reservations"][0]["Instances"][0]


def test_instance_in_correct_vpc(ec2, outputs):
    assert ec2["VpcId"] == outputs["expected_vpc_id"]


def test_instance_in_correct_subnet(ec2, outputs):
    assert ec2["SubnetId"] == outputs["expected_subnet_id"]


def test_security_group_in_correct_vpc(outputs, aws_region):
    ec2_client = boto3.client("ec2", region_name=aws_region)
    sg = ec2_client.describe_security_groups(
        GroupIds=[outputs["security_group_id"]]
    )["SecurityGroups"][0]
    assert sg["VpcId"] == outputs["expected_vpc_id"]
