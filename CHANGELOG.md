# Changelog

## [1.0.2] - 2026-07-02

### Bug Fixes

- Fix tailnet DNS switching before AdGuard Home is ready: add `null_resource` with `remote-exec` that SSHs into the instance and polls `/tmp/bootstrap-complete` before setting `tailscale_dns_nameservers`, preventing internet loss during deployment when AdGuard is enabled

### Changes

- Add `hashicorp/null ~> 3.0` provider dependency (used for bootstrap gate)

## [1.0.0] - 2026-06-25

### Features

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

## v1.0.2 (2026-07-01)

### Fix

- gate tailnet DNS on AdGuard bootstrap completion

## v1.0.1 (2026-06-25)

### Fix

- correct security group description charset and stabilise CI workflows
- resolve CI pipeline failures across lint, validate, and test jobs

## v1.0.0 (2026-06-25)

### Feat

- add tailscale_hostname input; remove infracost workflow
- initial release of terraform-aws-tailscale-exit-node module
