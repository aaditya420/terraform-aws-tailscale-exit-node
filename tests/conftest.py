"""Shared fixtures for all Terraform module integration tests."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
from python_terraform import Terraform

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def pytest_addoption(parser):
    parser.addoption("--tailscale-api-key", default=os.environ.get("TAILSCALE_API_KEY"))
    parser.addoption("--aws-region", default=os.environ.get("AWS_DEFAULT_REGION", "eu-west-3"))


@pytest.fixture(scope="session")
def tailscale_api_key(request):
    key = request.config.getoption("--tailscale-api-key")
    if not key:
        pytest.skip("No TAILSCALE_API_KEY — skipping integration tests")
    return key


@pytest.fixture(scope="session")
def aws_region(request):
    return request.config.getoption("--aws-region")


def _make_tf_fixture(scenario: str):
    """Factory that returns a module-scoped fixture for a named scenario."""

    @pytest.fixture(scope="module")
    def tf_outputs(tailscale_api_key, aws_region):
        working_dir = str(SCENARIOS_DIR / scenario)
        tf = Terraform(working_dir=working_dir)
        tf_vars = {"tailscale_api_key": tailscale_api_key, "aws_region": aws_region}

        rc, _, stderr = tf.init(reconfigure=True, capture_output=True)
        assert rc == 0, f"terraform init failed:\n{stderr}"

        try:
            rc, _, stderr = tf.apply(
                skip_plan=True,
                auto_approve=True,
                var=tf_vars,
                capture_output=True,
            )
            assert rc == 0, f"terraform apply failed:\n{stderr}"

            # python-terraform's output() returns the parsed dict on success,
            # not a (rc, stdout, stderr) tuple — use subprocess to avoid that quirk.
            proc = subprocess.run(
                ["terraform", "output", "-json"],
                cwd=working_dir,
                capture_output=True,
                text=True,
            )
            assert proc.returncode == 0, f"terraform output failed:\n{proc.stderr}"
            outputs = json.loads(proc.stdout)
            # Unwrap: {"key": {"value": ..., "sensitive": ...}} → {"key": ...}
            yield {k: v["value"] for k, v in outputs.items()}
        finally:
            # python_terraform uses deprecated -force flag; call terraform directly.
            subprocess.run(
                ["terraform", "destroy", "-auto-approve", "-input=false"],
                cwd=working_dir,
                env={
                    **os.environ,
                    "TF_VAR_tailscale_api_key": tailscale_api_key,
                    "TF_VAR_aws_region": aws_region,
                },
                check=False,
            )

    return tf_outputs


# Expose per-scenario fixtures
basic_outputs      = _make_tf_fixture("basic")
complete_outputs   = _make_tf_fixture("complete")
no_adguard_outputs = _make_tf_fixture("no_adguard")
x86_outputs        = _make_tf_fixture("x86_64")
custom_vpc_outputs = _make_tf_fixture("custom_vpc")


# ── Helpers re-exported for convenience ──────────────────────────────────────

from python_terraform import IsFlagged  # noqa: E402  (used above)
