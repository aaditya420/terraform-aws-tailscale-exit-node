# terraform-aws-tailscale-exit-node

A production-ready Terraform module that deploys a fully automated Tailscale VPN exit node on AWS EC2, with AdGuard Home for DNS-level ad and tracker blocking — all wired together end-to-end with zero manual steps after `terraform apply`.

## What it does

```
terraform apply
     │
     ├── Creates Tailscale ACL with autoApprovers (exit node routes auto-approved)
     ├── Generates a tagged pre-auth key dynamically (no manual key management)
     ├── Launches t4g.nano EC2 (ARM64 Graviton2, ~$3.50/mo in eu-west-3)
     │     └── user_data bootstraps:
     │           ├── IP forwarding
     │           ├── Tailscale (joins tailnet, advertises exit node, auto-approved)
     │           └── AdGuard Home (installed + fully configured via API)
     ├── Waits for device to appear in tailnet (up to 5 min)
     ├── Sets AdGuard Home's Tailscale IP as tailnet-wide DNS nameserver
     └── Outputs: tailscale_ip, adguard_url, adguard_password, ssh_command
```

## Why this module is unique

No other published Terraform module on the registry combines:
- **AWS EC2** (not GCP, not Lightsail, not Fargate)
- **Exit node** (not just subnet router)
- **ARM64/Graviton2** (cost-optimised; x86_64 also supported)
- **AdGuard Home** with full API automation — no wizard, no browser
- **Tailscale provider** for ACL, auto-approval, and DNS nameserver — no manual steps

## Requirements

| Tool | Version |
|---|---|
| Terraform | >= 1.5 |
| AWS provider | ~> 5.0 |
| Tailscale provider | ~> 0.16 |

**Before applying:**
1. An AWS account with IAM credentials in your environment (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`)
2. A Tailscale account with a personal API key from `login.tailscale.com/admin/settings/keys`

## Usage

### Minimal (all defaults)

```hcl
module "exit_node" {
  source  = "your-namespace/tailscale-exit-node/aws"
  version = "~> 1.0"

  region            = "eu-west-3"
  tailscale_api_key = var.tailscale_api_key
}

output "adguard_url" { value = module.exit_node.adguard_url }
output "tailscale_ip" { value = module.exit_node.tailscale_ip }
output "adguard_password" {
  value     = module.exit_node.adguard_password
  sensitive = true
}
```

After apply, retrieve credentials:
```bash
terraform output tailscale_ip
terraform output -raw adguard_password
```

### Complete (all options)

```hcl
module "exit_node" {
  source  = "your-namespace/tailscale-exit-node/aws"
  version = "~> 1.0"

  region                = "us-east-1"
  availability_zone     = "us-east-1b"
  name_prefix           = "my-vpn"
  tags                  = { Environment = "prod" }

  instance_type         = "t4g.micro"
  instance_architecture = "arm64"
  root_volume_size_gb   = 10

  tailscale_api_key            = var.tailscale_api_key
  tailscale_exit_node_tag      = "tag:exit-node"
  tailscale_key_expiry_seconds = 7776000
  enable_magic_dns             = true
  set_adguard_as_tailnet_dns   = true

  adguard_enabled             = true
  adguard_version             = "latest"
  adguard_username            = "admin"
  adguard_password            = var.adguard_password   # omit for auto-generated
  adguard_upstream_dns        = ["https://dns10.quad9.net/dns-query"]
  adguard_enable_safe_browsing = false
  adguard_stats_interval_days  = 7
}
```

### AdGuard disabled (plain exit node only)

```hcl
module "exit_node" {
  source  = "your-namespace/tailscale-exit-node/aws"
  version = "~> 1.0"

  region                     = "ap-south-1"
  tailscale_api_key          = var.tailscale_api_key
  adguard_enabled            = false
  set_adguard_as_tailnet_dns = false
}
```

## Save the SSH key locally

The module exposes the private key as a sensitive output. Save it from your root config:

```hcl
resource "local_file" "key" {
  content         = module.exit_node.private_key_pem
  filename        = "${path.module}/exit-node.pem"
  file_permission = "0400"
}
```

## Costs

| Instance | Region | On-demand/month |
|---|---|---|
| t4g.nano (ARM64) | eu-west-3 | ~$3.50 |
| t4g.micro (ARM64) | eu-west-3 | ~$7.00 |
| t3.micro (x86) | eu-west-3 | ~$8.50 |

Storage (8 GiB gp3) adds ~$0.64/month.

<!-- BEGIN_TF_DOCS -->
<!-- END_TF_DOCS -->

## Architecture decision notes

- `source_dest_check = false` is mandatory on the EC2 interface for exit node packet forwarding
- The Tailscale install script uses `set -e` internally; the user_data script intentionally does NOT use `set -e` to avoid early termination when piping the install script
- systemd-resolved's stub listener is disabled and `/etc/resolv.conf` re-symlinked before AdGuard Home starts, so port 53 is free
- The `tailscale_tailnet_key` resource depends on `tailscale_acl` to ensure the tag exists before the key is generated with that tag
- `tailscale_dns_nameservers` depends on `tailscale_dns_preferences` (MagicDNS) to ensure the preference is applied before nameservers propagate

## Publishing to the Terraform Registry

1. Create a public GitHub repo named exactly `terraform-aws-tailscale-exit-node`
2. Push this code with at least one `v*` tag (`git tag v1.0.0 && git push --tags`)
3. Go to `registry.terraform.io` → sign in with GitHub → Publish → Module → select the repo
4. The registry indexes within ~10 minutes of each new tag

## License

MIT — see [LICENSE](LICENSE).
