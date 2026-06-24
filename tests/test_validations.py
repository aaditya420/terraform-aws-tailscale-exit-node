"""Negative tests — verify bad inputs cause terraform plan to fail with useful errors.
These tests do NOT deploy any infrastructure.
"""
import os
from pathlib import Path

import pytest
from python_terraform import Terraform

INVALID = Path(__file__).parent / "scenarios" / "invalid_inputs"


def plan_fails_with(scenario_subdir: str, expected_fragment: str):
    """Run terraform plan in scenario_subdir and assert it fails with expected_fragment in stderr."""
    tf = Terraform(working_dir=str(INVALID / scenario_subdir))
    rc, _, stderr = tf.init(reconfigure=True, backend=False, capture_output=True)
    assert rc == 0, f"init failed: {stderr}"
    rc, _, stderr = tf.plan(
        var={"tailscale_api_key": "dummy", "aws_region": "eu-west-3"},
        capture_output=True,
        detailed_exitcode=True,
    )
    # Exit codes: 0=no changes, 1=error, 2=changes present. We expect 1 (error).
    assert rc == 1, f"Expected plan to fail but got exit code {rc}.\nstderr:\n{stderr}"
    assert expected_fragment.lower() in stderr.lower(), (
        f"Expected '{expected_fragment}' in plan error output.\nActual stderr:\n{stderr}"
    )


def test_graviton_type_with_x86_arch_fails():
    plan_fails_with("bad_arch", "arm64")


def test_volume_size_below_minimum_fails():
    plan_fails_with("small_volume", "at least 8")


def test_invalid_cidr_fails():
    plan_fails_with("bad_cidr", "valid cidr")


def test_adguard_port_53_conflict_fails():
    plan_fails_with("dns_port_conflict", "reserved for dns")


def test_tag_without_prefix_fails():
    plan_fails_with("bad_tag_format", "tag:")


def test_empty_api_key_fails():
    """Empty tailscale_api_key must fail variable validation."""
    tf = Terraform(working_dir=str(INVALID / "bad_arch"))
    tf.init(reconfigure=True, backend=False, capture_output=True)
    rc, _, stderr = tf.plan(
        var={"tailscale_api_key": "", "aws_region": "eu-west-3"},
        capture_output=True,
        detailed_exitcode=True,
    )
    assert rc == 1
    assert "must not be empty" in stderr.lower()


def test_invalid_timeout_format_fails():
    """device_join_timeout must match ^\d+[sm]$."""
    tf = Terraform(working_dir=str(INVALID / "bad_arch"))
    tf.init(reconfigure=True, backend=False, capture_output=True)
    rc, _, stderr = tf.plan(
        var={"tailscale_api_key": "dummy", "aws_region": "eu-west-3",
             "device_join_timeout": "3minutes"},
        capture_output=True,
        detailed_exitcode=True,
    )
    assert rc == 1
    assert "device_join_timeout" in stderr.lower()
