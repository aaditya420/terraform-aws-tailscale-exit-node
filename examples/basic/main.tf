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

  region            = "eu-west-3"
  tailscale_api_key = var.tailscale_api_key
}

variable "tailscale_api_key" {
  type      = string
  sensitive = true
}

output "adguard_url"   { value = module.exit_node.adguard_url }
output "tailscale_ip"  { value = module.exit_node.tailscale_ip }
output "ssh_command"   { value = module.exit_node.ssh_command }
output "adguard_password" {
  value     = module.exit_node.adguard_password
  sensitive = true
}

resource "local_file" "private_key" {
  content         = module.exit_node.private_key_pem
  filename        = "${path.module}/exit-node.pem"
  file_permission = "0400"
}
