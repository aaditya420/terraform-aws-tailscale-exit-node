locals {
  # AZ: use explicit input or first available in the region
  availability_zone = var.availability_zone != "" ? var.availability_zone : data.aws_availability_zones.available.names[0]

  # VPC / subnet: explicit inputs win over default-VPC lookups
  vpc_id    = var.vpc_id != null ? var.vpc_id : data.aws_vpc.default[0].id
  subnet_id = var.subnet_id != null ? var.subnet_id : data.aws_subnet.default[0].id

  # AMI: explicit override or auto-lookup by architecture.
  # Ubuntu uses "amd64" in AMI names where Terraform/AWS calls the arch "x86_64".
  ubuntu_ami_arch = var.instance_architecture == "arm64" ? "arm64" : "amd64"
  ami_id          = var.ami_id != null ? var.ami_id : data.aws_ami.ubuntu[0].id
  ami_name_filter = var.ami_name_filter != null ? var.ami_name_filter : "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-${local.ubuntu_ami_arch}-server-*"

  # AdGuard Home password: explicit input or auto-generated
  adguard_password = var.adguard_password != null ? var.adguard_password : (
    var.adguard_enabled ? random_password.adguard[0].result : ""
  )

  # AdGuard Home architecture suffix matches GitHub release naming
  adguard_arch = var.instance_architecture == "arm64" ? "arm64" : "amd64"

  # AdGuard Home download URL
  adguard_download_url = var.adguard_version == "latest" ? (
    "https://github.com/AdguardTeam/AdGuardHome/releases/latest/download/AdGuardHome_linux_${local.adguard_arch}.tar.gz"
    ) : (
    "https://github.com/AdguardTeam/AdGuardHome/releases/download/${var.adguard_version}/AdGuardHome_linux_${local.adguard_arch}.tar.gz"
  )

  # Default ACL policy — allow-all with tag ownership + autoApprovers
  default_acl_policy = jsonencode({
    tagOwners = {
      (var.tailscale_exit_node_tag) = ["autogroup:admin"]
    }
    autoApprovers = {
      exitNode = [var.tailscale_exit_node_tag]
    }
    acls = [{
      action = "accept"
      src    = ["*"]
      dst    = ["*:*"]
    }]
  })

  acl_policy = var.tailscale_acl_policy != null ? var.tailscale_acl_policy : local.default_acl_policy

  # EC2 key name: generated or supplied
  key_name = var.create_ssh_keypair ? aws_key_pair.main[0].key_name : var.existing_key_name

  # Common tags applied to every resource
  common_tags = merge(
    { Name = var.name_prefix },
    var.tags
  )

  # Tailscale device name: use friendly input if provided, else fall back to the
  # AWS-generated ip-x-x-x-x hostname that Ubuntu sets automatically.
  tailscale_device_name = var.tailscale_hostname != null ? var.tailscale_hostname : "ip-${replace(aws_instance.tailscale_exit_node.private_ip, ".", "-")}"

  # Parse API response to extract IP and ID for the matched device.
  ts_devices              = jsondecode(data.http.tailscale_devices.response_body).devices
  tailscale_device        = [for d in local.ts_devices : d if d.hostname == local.tailscale_device_name][0]
  tailscale_device_ip     = local.tailscale_device.addresses[0]
  tailscale_device_id_val = local.tailscale_device.id

  # Stats interval in hours for AdGuard API
  adguard_stats_interval_hours = var.adguard_stats_interval_days * 24
}
