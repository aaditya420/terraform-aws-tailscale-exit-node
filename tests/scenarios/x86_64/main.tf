terraform {
  required_providers {
    aws       = { source = "hashicorp/aws",       version = "~> 5.0" }
    tailscale = { source = "tailscale/tailscale", version = "~> 0.16" }
    tls       = { source = "hashicorp/tls",       version = "~> 4.0" }
    random    = { source = "hashicorp/random",    version = "~> 3.0" }
    http      = { source = "hashicorp/http",      version = "~> 3.0" }
  }
}

variable "tailscale_api_key" {
  type      = string
  sensitive = true
}

variable "aws_region" {
  type    = string
  default = "eu-west-3"
}

variable "run_id" {
  type    = string
  default = "local"
}

module "exit_node" {
  source                = "../../../"
  region                = var.aws_region
  tailscale_api_key     = var.tailscale_api_key
  name_prefix           = "ci-x86-${var.run_id}"
  instance_type         = "t3.micro"
  instance_architecture = "x86_64"
  tailscale_hostname    = "ci-x86-${var.run_id}"
  manage_tailscale_acl       = false
  set_adguard_as_tailnet_dns = false
  device_join_timeout        = "600s"
}

output "instance_id"        { value = module.exit_node.instance_id }
output "instance_public_ip" { value = module.exit_node.instance_public_ip }
output "tailscale_ip"       { value = module.exit_node.tailscale_ip }
output "adguard_url"        { value = module.exit_node.adguard_url }
output "adguard_username"   { value = module.exit_node.adguard_username }
output "adguard_password" {
  value     = module.exit_node.adguard_password
  sensitive = true
}
output "private_key_pem" {
  value     = module.exit_node.private_key_pem
  sensitive = true
}
output "ami_id" { value = module.exit_node.ami_id }
