provider "aws" {
  region = var.region
}

provider "tailscale" {
  api_key = var.tailscale_api_key
}

# ─── Data sources ─────────────────────────────────────────────────────────────

data "aws_availability_zones" "available" {
  #checkov:skip=CKV_AWS_394:Region-agnostic module. Zone names differ per region, so they cannot be pinned here; only the first zone is used, and only when availability_zone is unset.
  state = "available"
}

data "aws_vpc" "default" {
  count   = var.vpc_id == null ? 1 : 0
  default = true
}

data "aws_subnet" "default" {
  count             = var.subnet_id == null ? 1 : 0
  vpc_id            = local.vpc_id
  availability_zone = local.availability_zone
  default_for_az    = true
}

data "aws_ami" "ubuntu" {
  count       = var.ami_id == null ? 1 : 0
  most_recent = true
  owners      = [var.ami_owner_id]

  filter {
    name   = "name"
    values = [local.ami_name_filter]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  filter {
    name   = "architecture"
    values = [var.instance_architecture]
  }
}

# ─── AdGuard Home password ────────────────────────────────────────────────────

resource "random_password" "adguard" {
  count   = var.adguard_enabled && var.adguard_password == null ? 1 : 0
  length  = 20
  special = true
  # Exclude chars that break shell quoting inside the user_data template
  override_special = "!@#%^&*()-_=+[]"
}

# ─── SSH key pair ─────────────────────────────────────────────────────────────

resource "tls_private_key" "ssh" {
  count     = var.create_ssh_keypair ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "main" {
  count      = var.create_ssh_keypair ? 1 : 0
  key_name   = "${var.name_prefix}-key"
  public_key = tls_private_key.ssh[0].public_key_openssh
  tags       = local.common_tags
}

# ─── Security group ──────────────────────────────────────────────────────────

resource "aws_security_group" "tailscale" {
  name        = "${var.name_prefix}-sg"
  description = "Tailscale exit node - WireGuard + SSH"
  vpc_id      = local.vpc_id

  ingress {
    description = "Tailscale WireGuard"
    from_port   = 41641
    to_port     = 41641
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  #checkov:skip=CKV_AWS_24:SSH source CIDR is intentionally user-controlled via ssh_allowed_cidr_blocks variable
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidr_blocks
  }

  #checkov:skip=CKV_AWS_382:Exit node must forward arbitrary outbound traffic — restricting egress breaks VPN functionality
  egress {
    description = "All outbound traffic - required for VPN exit node packet forwarding."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-sg" })
}

# ─── Tailscale ACL ───────────────────────────────────────────────────────────

resource "tailscale_acl" "main" {
  count                      = var.manage_tailscale_acl ? 1 : 0
  acl                        = local.acl_policy
  overwrite_existing_content = true
}

# ─── Tailscale auth key (generated, tagged, pre-authorised) ──────────────────

resource "tailscale_tailnet_key" "exit_node" {
  reusable      = false
  ephemeral     = false
  preauthorized = true
  expiry        = var.tailscale_key_expiry_seconds
  tags          = [var.tailscale_exit_node_tag]

  depends_on = [tailscale_acl.main]
}

# ─── CloudWatch Agent IAM role ───────────────────────────────────────────────

data "aws_iam_policy_document" "cloudwatch_agent_assume" {
  count = var.cloudwatch_agent_enabled ? 1 : 0

  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# cloudwatch:PutMetricData has no resource-level permissions in IAM — "*" is
# required by the action itself, not an over-broad grant.
data "aws_iam_policy_document" "cloudwatch_agent" {
  count = var.cloudwatch_agent_enabled ? 1 : 0

  #checkov:skip=CKV_AWS_111:cloudwatch:PutMetricData does not support resource-level permissions
  #checkov:skip=CKV_AWS_356:cloudwatch:PutMetricData does not support resource-level permissions
  statement {
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
  }
}

resource "aws_iam_role" "cloudwatch_agent" {
  count              = var.cloudwatch_agent_enabled ? 1 : 0
  name               = "${var.name_prefix}-cwagent"
  assume_role_policy = data.aws_iam_policy_document.cloudwatch_agent_assume[0].json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "cloudwatch_agent" {
  count  = var.cloudwatch_agent_enabled ? 1 : 0
  name   = "${var.name_prefix}-cwagent-put-metric-data"
  role   = aws_iam_role.cloudwatch_agent[0].id
  policy = data.aws_iam_policy_document.cloudwatch_agent[0].json
}

resource "aws_iam_instance_profile" "cloudwatch_agent" {
  count = var.cloudwatch_agent_enabled ? 1 : 0
  name  = "${var.name_prefix}-cwagent"
  role  = aws_iam_role.cloudwatch_agent[0].name
  tags  = local.common_tags
}

# ─── EC2 instance ─────────────────────────────────────────────────────────────

resource "aws_instance" "tailscale_exit_node" {
  ami           = local.ami_id
  instance_type = var.instance_type
  # When subnet_id is explicit the subnet's AZ takes precedence; setting both
  # would conflict if they differ (e.g. user picks subnet in AZ-b but the
  # default AZ lookup resolves AZ-a).
  availability_zone = var.subnet_id == null ? local.availability_zone : null
  subnet_id         = local.subnet_id
  key_name          = local.key_name

  vpc_security_group_ids = [aws_security_group.tailscale.id]
  iam_instance_profile   = var.cloudwatch_agent_enabled ? aws_iam_instance_profile.cloudwatch_agent[0].name : null

  # Mandatory for exit node — forwards packets destined for other hosts
  source_dest_check = false

  monitoring    = true
  ebs_optimized = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  user_data_replace_on_change = true
  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    tailscale_auth_key      = tailscale_tailnet_key.exit_node.key
    tailscale_tag           = var.tailscale_exit_node_tag
    tailscale_hostname      = var.tailscale_hostname
    tailscale_accept_routes = var.tailscale_accept_routes
    tailscale_accept_dns    = var.tailscale_accept_dns

    adguard_enabled              = var.adguard_enabled
    adguard_download_url         = local.adguard_download_url
    adguard_web_port             = var.adguard_web_port
    adguard_username             = var.adguard_username
    adguard_password             = local.adguard_password
    adguard_upstream_dns_json    = jsonencode(var.adguard_upstream_dns)
    adguard_fallback_dns_json    = jsonencode(var.adguard_fallback_dns)
    adguard_blocklist_urls       = var.adguard_blocklist_urls
    adguard_enable_safe_browsing = var.adguard_enable_safe_browsing
    adguard_enable_safesearch    = var.adguard_enable_safesearch
    adguard_query_log_enabled    = var.adguard_query_log_enabled
    adguard_stats_interval_hours = local.adguard_stats_interval_hours

    cloudwatch_agent_enabled               = var.cloudwatch_agent_enabled
    cloudwatch_agent_arch                  = local.cloudwatch_agent_arch
    cloudwatch_namespace                   = var.cloudwatch_namespace
    cloudwatch_metrics_collection_interval = var.cloudwatch_metrics_collection_interval
  })

  root_block_device {
    volume_type = var.root_volume_type
    volume_size = var.root_volume_size_gb
    encrypted   = var.root_volume_encrypted
  }

  tags = local.common_tags

  lifecycle {
    precondition {
      condition = !(
        can(regex("^(t4g|c6g|c7g|m6g|m7g|r6g|r7g|x2g|im4g|is4gen)\\.", var.instance_type)) &&
        var.instance_architecture != "arm64"
      )
      error_message = "Graviton instance types (t4g, c6g, c7g, m6g, m7g, r6g, r7g …) require instance_architecture = \"arm64\"."
    }

    precondition {
      condition     = var.create_ssh_keypair || var.existing_key_name != null
      error_message = "Set create_ssh_keypair = true or provide an existing_key_name."
    }
  }
}

# ─── Wait for EC2 user_data to run and the device to join the tailnet ────────
# Using time_sleep (hashicorp/time) instead of data.tailscale_device.wait_for
# because tailscale/tailscale v0.29+ runs provider-framework validators during
# terraform validate with null values, causing any variable reference on wait_for
# to fail with "unable to parse value as a duration". time_sleep uses the
# older plugin-SDK and does not have this limitation.

resource "time_sleep" "wait_for_device" {
  depends_on      = [aws_instance.tailscale_exit_node]
  create_duration = var.device_join_timeout

  # Without this, time_sleep has no attribute tied to the instance, so once
  # created it never sleeps again — replacing the instance (e.g. a user_data
  # change) skips the wait entirely and the device-join check below fires
  # before the new instance has even finished booting.
  triggers = {
    instance_id = aws_instance.tailscale_exit_node.id
  }
}

# ─── Tailscale device lookup via API (hostname-based, provider-version agnostic) ─

data "http" "tailscale_devices" {
  url    = "https://api.tailscale.com/api/v2/tailnet/-/devices"
  method = "GET"
  request_headers = {
    "Authorization" = "Bearer ${var.tailscale_api_key}"
    "Accept"        = "application/json"
  }
  depends_on = [time_sleep.wait_for_device]

  lifecycle {
    postcondition {
      condition = contains(
        [for d in jsondecode(self.response_body).devices : d.hostname],
        local.tailscale_device_name
      )
      error_message = "Device '${local.tailscale_device_name}' not found in tailnet after ${var.device_join_timeout}. Verify the EC2 instance user_data ran successfully."
    }
  }
}

# ─── Wait for AdGuard Home bootstrap to complete before setting DNS ───────────
# SSHs into the instance and polls /tmp/bootstrap-complete (written by
# user_data at the very end) so tailnet DNS is only switched over once
# AdGuard is fully configured and serving on port 53.
# Only active when AdGuard is enabled, DNS will be set, and we own the key.
# Falls back to time_sleep-only ordering when create_ssh_keypair = false.

resource "null_resource" "wait_for_bootstrap" {
  count      = var.adguard_enabled && var.set_adguard_as_tailnet_dns && var.create_ssh_keypair ? 1 : 0
  depends_on = [time_sleep.wait_for_device]

  # Same issue as time_sleep.wait_for_device above: without a trigger tied to
  # the instance, this only ever polls once, on first creation. Replacing the
  # instance would otherwise leave Terraform treating the old instance's
  # successful poll as still satisfied, never re-checking the new one's
  # bootstrap at all.
  triggers = {
    instance_id = aws_instance.tailscale_exit_node.id
  }

  connection {
    type        = "ssh"
    user        = "ubuntu"
    host        = aws_instance.tailscale_exit_node.public_ip
    private_key = tls_private_key.ssh[0].private_key_pem
    timeout     = "10m"
  }

  provisioner "remote-exec" {
    inline = ["timeout 600 bash -c 'until [ -f /tmp/bootstrap-complete ]; do sleep 5; done'"]
  }
}

# ─── Tailscale DNS automation ────────────────────────────────────────────────

resource "tailscale_dns_preferences" "main" {
  count     = var.enable_magic_dns ? 1 : 0
  magic_dns = true
}

resource "tailscale_dns_nameservers" "adguard" {
  count       = var.adguard_enabled && var.set_adguard_as_tailnet_dns ? 1 : 0
  nameservers = [local.tailscale_device_ip]

  depends_on = [
    tailscale_dns_preferences.main,
    null_resource.wait_for_bootstrap,
  ]
}
