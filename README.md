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
  source  = "aaditya420/tailscale-exit-node/aws"
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
  source  = "aaditya420/tailscale-exit-node/aws"
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
  source  = "aaditya420/tailscale-exit-node/aws"
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
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 5.0 |
| <a name="requirement_http"></a> [http](#requirement\_http) | ~> 3.0 |
| <a name="requirement_random"></a> [random](#requirement\_random) | ~> 3.0 |
| <a name="requirement_tailscale"></a> [tailscale](#requirement\_tailscale) | ~> 0.16 |
| <a name="requirement_time"></a> [time](#requirement\_time) | ~> 0.9 |
| <a name="requirement_tls"></a> [tls](#requirement\_tls) | ~> 4.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 5.0 |
| <a name="provider_http"></a> [http](#provider\_http) | ~> 3.0 |
| <a name="provider_random"></a> [random](#provider\_random) | ~> 3.0 |
| <a name="provider_tailscale"></a> [tailscale](#provider\_tailscale) | ~> 0.16 |
| <a name="provider_time"></a> [time](#provider\_time) | ~> 0.9 |
| <a name="provider_tls"></a> [tls](#provider\_tls) | ~> 4.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_instance.tailscale_exit_node](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/instance) | resource |
| [aws_key_pair.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/key_pair) | resource |
| [aws_security_group.tailscale](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group) | resource |
| [random_password.adguard](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/password) | resource |
| [tailscale_acl.main](https://registry.terraform.io/providers/tailscale/tailscale/latest/docs/resources/acl) | resource |
| [tailscale_dns_nameservers.adguard](https://registry.terraform.io/providers/tailscale/tailscale/latest/docs/resources/dns_nameservers) | resource |
| [tailscale_dns_preferences.main](https://registry.terraform.io/providers/tailscale/tailscale/latest/docs/resources/dns_preferences) | resource |
| [tailscale_tailnet_key.exit_node](https://registry.terraform.io/providers/tailscale/tailscale/latest/docs/resources/tailnet_key) | resource |
| [time_sleep.wait_for_device](https://registry.terraform.io/providers/hashicorp/time/latest/docs/resources/sleep) | resource |
| [tls_private_key.ssh](https://registry.terraform.io/providers/hashicorp/tls/latest/docs/resources/private_key) | resource |
| [aws_ami.ubuntu](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ami) | data source |
| [aws_availability_zones.available](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/availability_zones) | data source |
| [aws_subnet.default](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/subnet) | data source |
| [aws_vpc.default](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc) | data source |
| [http_http.tailscale_devices](https://registry.terraform.io/providers/hashicorp/http/latest/docs/data-sources/http) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_adguard_blocklist_urls"></a> [adguard\_blocklist\_urls](#input\_adguard\_blocklist\_urls) | Filter list URLs to add to AdGuard Home on first boot. | `list(string)` | <pre>[<br/>  "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt",<br/>  "https://adguardteam.github.io/HostlistsRegistry/assets/filter_2.txt",<br/>  "https://easylist.to/easylist/easylist.txt"<br/>]</pre> | no |
| <a name="input_adguard_enable_safe_browsing"></a> [adguard\_enable\_safe\_browsing](#input\_adguard\_enable\_safe\_browsing) | Enable AdGuard Home safe browsing (blocks malware/phishing domains). | `bool` | `false` | no |
| <a name="input_adguard_enable_safesearch"></a> [adguard\_enable\_safesearch](#input\_adguard\_enable\_safesearch) | Enable safe search enforcement across search engines. | `bool` | `false` | no |
| <a name="input_adguard_enabled"></a> [adguard\_enabled](#input\_adguard\_enabled) | Install and configure AdGuard Home on the exit node. | `bool` | `true` | no |
| <a name="input_adguard_password"></a> [adguard\_password](#input\_adguard\_password) | Admin password for AdGuard Home. Auto-generated (20 chars, mixed) if null. | `string` | `null` | no |
| <a name="input_adguard_query_log_enabled"></a> [adguard\_query\_log\_enabled](#input\_adguard\_query\_log\_enabled) | Enable the query log in AdGuard Home. | `bool` | `true` | no |
| <a name="input_adguard_stats_interval_days"></a> [adguard\_stats\_interval\_days](#input\_adguard\_stats\_interval\_days) | Number of days to retain statistics in AdGuard Home. | `number` | `7` | no |
| <a name="input_adguard_upstream_dns"></a> [adguard\_upstream\_dns](#input\_adguard\_upstream\_dns) | Upstream DNS resolvers used by AdGuard Home. DoH and DoT URLs are supported. | `list(string)` | <pre>[<br/>  "https://dns10.quad9.net/dns-query",<br/>  "https://cloudflare-dns.com/dns-query"<br/>]</pre> | no |
| <a name="input_adguard_username"></a> [adguard\_username](#input\_adguard\_username) | Admin username for AdGuard Home. | `string` | `"admin"` | no |
| <a name="input_adguard_version"></a> [adguard\_version](#input\_adguard\_version) | AdGuard Home release to install. Use 'latest' or a pinned tag like 'v0.107.77'. | `string` | `"latest"` | no |
| <a name="input_adguard_web_port"></a> [adguard\_web\_port](#input\_adguard\_web\_port) | Port for the AdGuard Home web UI. Must not be 53. | `number` | `3000` | no |
| <a name="input_ami_id"></a> [ami\_id](#input\_ami\_id) | Override the auto-selected Ubuntu 22.04 AMI with a specific AMI ID. | `string` | `null` | no |
| <a name="input_ami_name_filter"></a> [ami\_name\_filter](#input\_ami\_name\_filter) | Glob filter for AMI name lookup. Defaults to Ubuntu 22.04 for the resolved architecture. | `string` | `null` | no |
| <a name="input_ami_owner_id"></a> [ami\_owner\_id](#input\_ami\_owner\_id) | AWS account ID that owns the AMI used for auto-lookup. Defaults to Canonical. | `string` | `"099720109477"` | no |
| <a name="input_availability_zone"></a> [availability\_zone](#input\_availability\_zone) | AZ for the instance. Defaults to the first available AZ in the selected region. | `string` | `""` | no |
| <a name="input_create_ssh_keypair"></a> [create\_ssh\_keypair](#input\_create\_ssh\_keypair) | Auto-generate an RSA key pair. Set false and supply existing\_key\_name to BYO key. | `bool` | `true` | no |
| <a name="input_device_join_timeout"></a> [device\_join\_timeout](#input\_device\_join\_timeout) | How long to poll for the device to appear in the tailnet after the instance boots. | `string` | `"300s"` | no |
| <a name="input_enable_magic_dns"></a> [enable\_magic\_dns](#input\_enable\_magic\_dns) | Enable MagicDNS across the tailnet so nameservers below are distributed. | `bool` | `true` | no |
| <a name="input_existing_key_name"></a> [existing\_key\_name](#input\_existing\_key\_name) | Name of an existing EC2 key pair to use when create\_ssh\_keypair is false. | `string` | `null` | no |
| <a name="input_instance_architecture"></a> [instance\_architecture](#input\_instance\_architecture) | CPU architecture for the instance and AMI lookup. Either arm64 or x86\_64. | `string` | `"arm64"` | no |
| <a name="input_instance_type"></a> [instance\_type](#input\_instance\_type) | EC2 instance type. Must match instance\_architecture (Graviton types require arm64). | `string` | `"t4g.nano"` | no |
| <a name="input_manage_tailscale_acl"></a> [manage\_tailscale\_acl](#input\_manage\_tailscale\_acl) | Let Terraform own the tailnet ACL. Set false if you manage ACL rules outside Terraform. | `bool` | `true` | no |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Prefix applied to every resource name and the Name tag. | `string` | `"tailscale-exit-node"` | no |
| <a name="input_region"></a> [region](#input\_region) | AWS region in which to deploy the exit node (e.g. eu-west-3, us-east-1). | `string` | n/a | yes |
| <a name="input_root_volume_encrypted"></a> [root\_volume\_encrypted](#input\_root\_volume\_encrypted) | Whether to encrypt the root EBS volume. | `bool` | `true` | no |
| <a name="input_root_volume_size_gb"></a> [root\_volume\_size\_gb](#input\_root\_volume\_size\_gb) | Root EBS volume size in GiB. Minimum 8. | `number` | `8` | no |
| <a name="input_root_volume_type"></a> [root\_volume\_type](#input\_root\_volume\_type) | EBS volume type for the root disk. | `string` | `"gp3"` | no |
| <a name="input_set_adguard_as_tailnet_dns"></a> [set\_adguard\_as\_tailnet\_dns](#input\_set\_adguard\_as\_tailnet\_dns) | Set AdGuard Home's Tailscale IP as the tailnet-wide DNS nameserver. | `bool` | `true` | no |
| <a name="input_ssh_allowed_cidr_blocks"></a> [ssh\_allowed\_cidr\_blocks](#input\_ssh\_allowed\_cidr\_blocks) | CIDR blocks allowed to reach TCP 22. Restrict to your IP for hardening. | `list(string)` | <pre>[<br/>  "0.0.0.0/0"<br/>]</pre> | no |
| <a name="input_subnet_id"></a> [subnet\_id](#input\_subnet\_id) | ID of an existing subnet. Omit to use the default subnet for the resolved AZ. | `string` | `null` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Additional tags merged onto every resource. | `map(string)` | `{}` | no |
| <a name="input_tailscale_accept_dns"></a> [tailscale\_accept\_dns](#input\_tailscale\_accept\_dns) | Pass --accept-dns to tailscale up. | `bool` | `true` | no |
| <a name="input_tailscale_accept_routes"></a> [tailscale\_accept\_routes](#input\_tailscale\_accept\_routes) | Pass --accept-routes to tailscale up. | `bool` | `true` | no |
| <a name="input_tailscale_acl_policy"></a> [tailscale\_acl\_policy](#input\_tailscale\_acl\_policy) | Full ACL JSON string. Defaults to allow-all with tag:exit-node autoApprovers. | `string` | `null` | no |
| <a name="input_tailscale_api_key"></a> [tailscale\_api\_key](#input\_tailscale\_api\_key) | Tailscale personal API key. Generate at login.tailscale.com/admin/settings/keys. | `string` | n/a | yes |
| <a name="input_tailscale_exit_node_tag"></a> [tailscale\_exit\_node\_tag](#input\_tailscale\_exit\_node\_tag) | Tailscale tag applied to the device and referenced by autoApprovers. | `string` | `"tag:exit-node"` | no |
| <a name="input_tailscale_hostname"></a> [tailscale\_hostname](#input\_tailscale\_hostname) | Custom Tailscale device name shown in the admin console and used for MagicDNS. Defaults to the EC2 private-IP hostname (ip-x-x-x-x). Set this to a friendly name like 'paris-exit' to make the device easy to identify. | `string` | `null` | no |
| <a name="input_tailscale_key_expiry_seconds"></a> [tailscale\_key\_expiry\_seconds](#input\_tailscale\_key\_expiry\_seconds) | Lifetime of the generated Tailscale pre-auth key in seconds. Default 90 days. | `number` | `7776000` | no |
| <a name="input_vpc_id"></a> [vpc\_id](#input\_vpc\_id) | ID of an existing VPC. Omit to use the region's default VPC. | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_adguard_password"></a> [adguard\_password](#output\_adguard\_password) | AdGuard Home admin password (sensitive). Retrieve with: terraform output -json adguard\_password |
| <a name="output_adguard_url"></a> [adguard\_url](#output\_adguard\_url) | AdGuard Home web UI URL (accessible over Tailscale). Empty when adguard\_enabled = false. |
| <a name="output_adguard_username"></a> [adguard\_username](#output\_adguard\_username) | AdGuard Home admin username. |
| <a name="output_ami_id"></a> [ami\_id](#output\_ami\_id) | AMI ID used to launch the instance. |
| <a name="output_instance_id"></a> [instance\_id](#output\_instance\_id) | EC2 instance ID of the exit node. |
| <a name="output_instance_private_ip"></a> [instance\_private\_ip](#output\_instance\_private\_ip) | Private IPv4 address of the exit node. |
| <a name="output_instance_public_ip"></a> [instance\_public\_ip](#output\_instance\_public\_ip) | Public IPv4 address of the exit node. |
| <a name="output_private_key_pem"></a> [private\_key\_pem](#output\_private\_key\_pem) | PEM-encoded RSA private key for SSH (sensitive). Null when create\_ssh\_keypair = false. |
| <a name="output_security_group_id"></a> [security\_group\_id](#output\_security\_group\_id) | ID of the security group attached to the exit node. |
| <a name="output_ssh_command"></a> [ssh\_command](#output\_ssh\_command) | SSH command to connect to the exit node. |
| <a name="output_tailscale_device_id"></a> [tailscale\_device\_id](#output\_tailscale\_device\_id) | Tailscale device ID. |
| <a name="output_tailscale_ip"></a> [tailscale\_ip](#output\_tailscale\_ip) | Tailscale IPv4 address (100.x.x.x) of the exit node. |
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
