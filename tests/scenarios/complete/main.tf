terraform {
  required_providers {
    aws       = { source = "hashicorp/aws",       version = "~> 5.0" }
    tailscale = { source = "tailscale/tailscale", version = "~> 0.16" }
    tls       = { source = "hashicorp/tls",       version = "~> 4.0" }
    random    = { source = "hashicorp/random",    version = "~> 3.0" }
  }
}

variable "tailscale_api_key" { type = string; sensitive = true }
variable "aws_region"        { type = string; default = "eu-west-3" }

module "exit_node" {
  source = "../../../"

  region                = var.aws_region
  name_prefix           = "ci-complete"
  tags                  = { Environment = "ci", Scenario = "complete" }
  instance_type         = "t4g.micro"
  instance_architecture = "arm64"
  root_volume_size_gb   = 10
  root_volume_encrypted = true
  tailscale_api_key            = var.tailscale_api_key
  tailscale_exit_node_tag      = "tag:exit-node"
  tailscale_key_expiry_seconds = 3600
  device_join_timeout          = "300s"
  enable_magic_dns             = true
  set_adguard_as_tailnet_dns   = true
  adguard_enabled              = true
  adguard_version              = "v0.107.77"
  adguard_web_port             = 3000
  adguard_username             = "testadmin"
  adguard_password             = "CiT3stP@ss!"
  adguard_upstream_dns         = ["https://dns10.quad9.net/dns-query"]
  adguard_blocklist_urls       = ["https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt"]
  adguard_query_log_enabled    = true
  adguard_stats_interval_days  = 7
}

output "instance_id"        { value = module.exit_node.instance_id }
output "instance_public_ip" { value = module.exit_node.instance_public_ip }
output "tailscale_ip"       { value = module.exit_node.tailscale_ip }
output "tailscale_device_id" { value = module.exit_node.tailscale_device_id }
output "adguard_url"        { value = module.exit_node.adguard_url }
output "adguard_username"   { value = module.exit_node.adguard_username }
output "adguard_password"   { value = module.exit_node.adguard_password; sensitive = true }
output "private_key_pem"    { value = module.exit_node.private_key_pem;  sensitive = true }
output "ssh_command"        { value = module.exit_node.ssh_command }
output "ami_id"             { value = module.exit_node.ami_id }
