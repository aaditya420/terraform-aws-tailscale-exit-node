"""Shared fixtures for all Terraform module integration tests."""
import json
import os
import subprocess
from pathlib import Path

import pytest

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
        env = {
            **os.environ,
            "TF_VAR_tailscale_api_key": tailscale_api_key,
            "TF_VAR_aws_region": aws_region,
            "TF_VAR_run_id": os.environ.get("TF_VAR_run_id", "local"),
        }

        init = subprocess.run(
            ["terraform", "init", "-reconfigure", "-input=false"],
            cwd=working_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        assert init.returncode == 0, f"terraform init failed:\n{init.stderr}"

        try:
            # Stream apply output to CI logs; not captured so it isn't interrupted
            # by pytest-timeout's SIGALRM mid-communicate().
            apply = subprocess.run(
                ["terraform", "apply", "-auto-approve", "-input=false"],
                cwd=working_dir,
                env=env,
            )
            assert apply.returncode == 0, "terraform apply failed (see output above)"

            out = subprocess.run(
                ["terraform", "output", "-json"],
                cwd=working_dir,
                capture_output=True,
                text=True,
            )
            assert out.returncode == 0, f"terraform output failed:\n{out.stderr}"
            outputs = json.loads(out.stdout)
            yield {k: v["value"] for k, v in outputs.items()}
        finally:
            # -lock=false handles stale state locks left by a SIGALRM-killed apply.
            subprocess.run(
                ["terraform", "destroy", "-auto-approve", "-input=false", "-lock=false"],
                cwd=working_dir,
                env=env,
                check=False,
            )

    return tf_outputs


# Expose per-scenario fixtures
basic_outputs      = _make_tf_fixture("basic")
complete_outputs   = _make_tf_fixture("complete")
no_adguard_outputs = _make_tf_fixture("no_adguard")
x86_outputs        = _make_tf_fixture("x86_64")
custom_vpc_outputs = _make_tf_fixture("custom_vpc")
