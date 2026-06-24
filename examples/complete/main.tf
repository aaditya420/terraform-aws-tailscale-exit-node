terraform {
  required_providers {
    aws       = { source = "hashicorp/aws",       version = "~> 5.0" }
    tailscale = { source = "tailscale/tailscale", version = "~> 0.16" }
    tls       = { source = "hashicorp/tls",       version = "~> 4.0" }
    random    = { source = "hashicorp/random",    version = "~> 3.0" }
  }
}

module "exit_node" {
  source = "../../"

  # ── Placement ──────────────────────────────────────────────────────────────
  region            = var.region
  availability_zone = var.availability_zone

  # ── Naming ─────────────────────────────────────────────────────────────────
  name_prefix = "my-exit-node"
  tags        = { Environment = "prod", Owner = "ops" }

  # ── Compute ────────────────────────────────────────────────────────────────
  instance_type         = "t4g.micro"
  instance_architecture = "arm64"
  root_volume_size_gb   = 10
  root_volume_encrypted = true

  # ── SSH ────────────────────────────────────────────────────────────────────
  ssh_allowed_cidr_blocks = ["0.0.0.0/0"]

  # ── Tailscale ──────────────────────────────────────────────────────────────
  tailscale_api_key            = var.tailscale_api_key
  tailscale_exit_node_tag      = "tag:exit-node"
  tailscale_accept_routes      = true
  tailscale_key_expiry_seconds = 7776000
  device_join_timeout          = "300s"
  enable_magic_dns             = true
  set_adguard_as_tailnet_dns   = true

  # ── AdGuard Home ───────────────────────────────────────────────────────────
  adguard_enabled             = true
  adguard_version             = "latest"
  adguard_web_port            = 3000
  adguard_username            = "admin"
  adguard_password            = var.adguard_password
  adguard_upstream_dns        = ["https://dns10.quad9.net/dns-query", "https://cloudflare-dns.com/dns-query"]
  adguard_enable_safe_browsing = false
  adguard_query_log_enabled   = true
  adguard_stats_interval_days = 7
  adguard_blocklist_urls = [
    "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt",
    "https://adguardteam.github.io/HostlistsRegistry/assets/filter_2.txt",
    "https://easylist.to/easylist/easylist.txt"
  ]
}

output "adguard_url"      { value = module.exit_node.adguard_url }
output "tailscale_ip"     { value = module.exit_node.tailscale_ip }
output "ssh_command"      { value = module.exit_node.ssh_command }
output "instance_id"      { value = module.exit_node.instance_id }
output "adguard_password" { value = module.exit_node.adguard_password; sensitive = true }

resource "local_file" "private_key" {
  content         = module.exit_node.private_key_pem
  filename        = "${path.module}/exit-node.pem"
  file_permission = "0400"
}
