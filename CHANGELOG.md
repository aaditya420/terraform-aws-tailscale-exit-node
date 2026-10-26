# Changelog

## v1.0.6 (2026-10-26)

### Feat

- Install and configure the CloudWatch Agent on first boot so memory, swap, and disk metrics are published to CloudWatch (EC2 reports CPU/network/disk I/O by default, but not memory) — gated by new `cloudwatch_agent_enabled` (default `true`)
- Add IAM role + instance profile scoped to `cloudwatch:PutMetricData`, attached to the instance only when `cloudwatch_agent_enabled = true`
- Add `cloudwatch_agent_enabled`, `cloudwatch_namespace`, and `cloudwatch_metrics_collection_interval` input variables

### Note

- Attaching the new instance profile and changing `user_data` means `terraform apply` will replace the running instance (new IAM role, new boot, re-join the tailnet)

## v1.0.5 (2026-10-21)

### Fix

- **docs**: use the Terraform Registry source and add README badges (#33)

## v1.0.4 (2026-10-21)

### Fix

- **examples**: split adguard_password output onto separate lines, so the Terraform Registry can parse the module (#30)

## v1.0.3 (2026-07-02)

### Fix

- Prevent OOM kills on low-memory instances (`t4g.nano`/`t4g.micro`): create a 512 MB swap file early in `user_data` so `unattended-upgrades` cannot exhaust RAM and destabilise AdGuard or sshd
- Prevent complete DNS outage when DoH upstreams are unavailable: configure AdGuard `fallback_dns` (default `["1.1.1.1", "9.9.9.9"]`) so plain DNS handles queries when Quad9/Cloudflare DoH time out

### Feat

- Add `adguard_fallback_dns` input variable (default `["1.1.1.1", "9.9.9.9"]`)

## v1.0.2 (2026-07-01)

### Fix

- Gate tailnet DNS on AdGuard bootstrap completion: a `null_resource` with `remote-exec` SSHs into the instance and polls `/tmp/bootstrap-complete` before setting `tailscale_dns_nameservers`, preventing internet loss during deployment when AdGuard is enabled
- Add the `hashicorp/null ~> 3.0` provider dependency (used for the bootstrap gate)

## v1.0.1 (2026-06-25)

### Fix

- correct security group description charset and stabilise CI workflows
- resolve CI pipeline failures across lint, validate, and test jobs

## v1.0.0 (2026-06-25)

### Feat

- EC2 Tailscale exit node on ARM64 Graviton2 (`t4g.nano` default) or x86_64
- Auto-selects Ubuntu 22.04 AMI by architecture; fully overridable
- Full Tailscale automation via `tailscale/tailscale` provider:
  - ACL with `autoApprovers` so exit node routes approve without manual clicks
  - Dynamically generated pre-auth key — no manual key management
  - `tailscale_device` data source waits for node to join tailnet
  - MagicDNS and tailnet-wide DNS nameserver set to AdGuard Home IP
- AdGuard Home fully configured via REST API on first boot:
  - Setup wizard auto-completed (no browser required)
  - Upstream DNS, blocklists, filtering, safe browsing, query log all wired in
  - Admin password auto-generated or user-supplied
- All inputs validated with `validation` blocks and `lifecycle.precondition`
- Works with default VPC or custom VPC/subnet
- Optional SSH key pair generation; BYO key supported
- add tailscale_hostname input; remove infracost workflow
