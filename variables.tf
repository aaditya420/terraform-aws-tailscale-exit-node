# ─── Required ────────────────────────────────────────────────────────────────

variable "tailscale_api_key" {
  description = "Tailscale personal API key. Generate at login.tailscale.com/admin/settings/keys."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.tailscale_api_key) > 0
    error_message = "tailscale_api_key must not be empty."
  }
}

variable "region" {
  description = "AWS region in which to deploy the exit node (e.g. eu-west-3, us-east-1)."
  type        = string
}

# ─── Placement ───────────────────────────────────────────────────────────────

variable "availability_zone" {
  description = "AZ for the instance. Defaults to the first available AZ in the selected region."
  type        = string
  default     = ""
}

variable "vpc_id" {
  description = "ID of an existing VPC. Omit to use the region's default VPC."
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "ID of an existing subnet. Omit to use the default subnet for the resolved AZ."
  type        = string
  default     = null
}

# ─── Naming & tagging ────────────────────────────────────────────────────────

variable "name_prefix" {
  description = "Prefix applied to every resource name and the Name tag."
  type        = string
  default     = "tailscale-exit-node"
}

variable "tags" {
  description = "Additional tags merged onto every resource."
  type        = map(string)
  default     = {}
}

# ─── Compute ─────────────────────────────────────────────────────────────────

variable "instance_type" {
  description = "EC2 instance type. Must match instance_architecture (Graviton types require arm64)."
  type        = string
  default     = "t4g.nano"
}

variable "instance_architecture" {
  description = "CPU architecture for the instance and AMI lookup. Either arm64 or x86_64."
  type        = string
  default     = "arm64"

  validation {
    condition     = contains(["arm64", "x86_64"], var.instance_architecture)
    error_message = "instance_architecture must be arm64 or x86_64."
  }
}

variable "ami_id" {
  description = "Override the auto-selected Ubuntu 22.04 AMI with a specific AMI ID."
  type        = string
  default     = null
}

variable "ami_owner_id" {
  description = "AWS account ID that owns the AMI used for auto-lookup. Defaults to Canonical."
  type        = string
  default     = "099720109477"
}

variable "ami_name_filter" {
  description = "Glob filter for AMI name lookup. Defaults to Ubuntu 22.04 for the resolved architecture."
  type        = string
  default     = null
}

variable "root_volume_size_gb" {
  description = "Root EBS volume size in GiB. Minimum 8."
  type        = number
  default     = 8

  validation {
    condition     = var.root_volume_size_gb >= 8
    error_message = "root_volume_size_gb must be at least 8 GiB."
  }
}

variable "root_volume_type" {
  description = "EBS volume type for the root disk."
  type        = string
  default     = "gp3"

  validation {
    condition     = contains(["gp2", "gp3"], var.root_volume_type)
    error_message = "root_volume_type must be gp2 or gp3."
  }
}

variable "root_volume_encrypted" {
  description = "Whether to encrypt the root EBS volume."
  type        = bool
  default     = true
}

# ─── SSH access ──────────────────────────────────────────────────────────────

variable "create_ssh_keypair" {
  description = "Auto-generate an RSA key pair. Set false and supply existing_key_name to BYO key."
  type        = bool
  default     = true
}

variable "existing_key_name" {
  description = "Name of an existing EC2 key pair to use when create_ssh_keypair is false."
  type        = string
  default     = null
}

variable "ssh_allowed_cidr_blocks" {
  description = "CIDR blocks allowed to reach TCP 22. Restrict to your IP for hardening."
  type        = list(string)
  default     = ["0.0.0.0/0"]

  validation {
    condition = alltrue([
      for cidr in var.ssh_allowed_cidr_blocks :
      can(cidrnetmask(cidr))
    ])
    error_message = "All entries in ssh_allowed_cidr_blocks must be valid CIDR notation."
  }
}

# ─── Tailscale ───────────────────────────────────────────────────────────────

variable "tailscale_exit_node_tag" {
  description = "Tailscale tag applied to the device and referenced by autoApprovers."
  type        = string
  default     = "tag:exit-node"

  validation {
    condition     = startswith(var.tailscale_exit_node_tag, "tag:")
    error_message = "tailscale_exit_node_tag must begin with 'tag:' (e.g. tag:exit-node)."
  }
}

variable "tailscale_accept_routes" {
  description = "Pass --accept-routes to tailscale up."
  type        = bool
  default     = true
}

variable "tailscale_accept_dns" {
  description = "Pass --accept-dns to tailscale up."
  type        = bool
  default     = true
}

variable "tailscale_key_expiry_seconds" {
  description = "Lifetime of the generated Tailscale pre-auth key in seconds. Default 90 days."
  type        = number
  default     = 7776000
}

variable "manage_tailscale_acl" {
  description = "Let Terraform own the tailnet ACL. Set false if you manage ACL rules outside Terraform."
  type        = bool
  default     = true
}

variable "tailscale_acl_policy" {
  description = "Full ACL JSON string. Defaults to allow-all with tag:exit-node autoApprovers."
  type        = string
  default     = null
}

variable "device_join_timeout" {
  description = "How long to poll for the device to appear in the tailnet after the instance boots."
  type        = string
  default     = "300s"

  validation {
    condition     = can(regex("^[0-9]+[sm]$", var.device_join_timeout))
    error_message = "device_join_timeout must be a number followed by s or m (e.g. 300s, 5m)."
  }
}

variable "enable_magic_dns" {
  description = "Enable MagicDNS across the tailnet so nameservers below are distributed."
  type        = bool
  default     = true
}

variable "set_adguard_as_tailnet_dns" {
  description = "Set AdGuard Home's Tailscale IP as the tailnet-wide DNS nameserver."
  type        = bool
  default     = true
}

# ─── AdGuard Home ────────────────────────────────────────────────────────────

variable "adguard_enabled" {
  description = "Install and configure AdGuard Home on the exit node."
  type        = bool
  default     = true
}

variable "adguard_version" {
  description = "AdGuard Home release to install. Use 'latest' or a pinned tag like 'v0.107.77'."
  type        = string
  default     = "latest"
}

variable "adguard_web_port" {
  description = "Port for the AdGuard Home web UI. Must not be 53."
  type        = number
  default     = 3000

  validation {
    condition     = var.adguard_web_port != 53
    error_message = "adguard_web_port must not be 53 — that port is reserved for DNS."
  }
}

variable "adguard_username" {
  description = "Admin username for AdGuard Home."
  type        = string
  default     = "admin"
}

variable "adguard_password" {
  description = "Admin password for AdGuard Home. Auto-generated (20 chars, mixed) if null."
  type        = string
  sensitive   = true
  default     = null
}

variable "adguard_upstream_dns" {
  description = "Upstream DNS resolvers used by AdGuard Home. DoH and DoT URLs are supported."
  type        = list(string)
  default = [
    "https://dns10.quad9.net/dns-query",
    "https://cloudflare-dns.com/dns-query"
  ]
}

variable "adguard_blocklist_urls" {
  description = "Filter list URLs to add to AdGuard Home on first boot."
  type        = list(string)
  default = [
    "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt",
    "https://adguardteam.github.io/HostlistsRegistry/assets/filter_2.txt",
    "https://easylist.to/easylist/easylist.txt"
  ]
}

variable "adguard_enable_safe_browsing" {
  description = "Enable AdGuard Home safe browsing (blocks malware/phishing domains)."
  type        = bool
  default     = false
}

variable "adguard_enable_safesearch" {
  description = "Enable safe search enforcement across search engines."
  type        = bool
  default     = false
}

variable "adguard_query_log_enabled" {
  description = "Enable the query log in AdGuard Home."
  type        = bool
  default     = true
}

variable "adguard_stats_interval_days" {
  description = "Number of days to retain statistics in AdGuard Home."
  type        = number
  default     = 7
}
