# Changelog

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
