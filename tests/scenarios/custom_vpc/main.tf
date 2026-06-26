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

# Use the default VPC explicitly to simulate a user-supplied VPC/subnet
data "aws_vpc" "default" { default = true }
data "aws_subnet" "default" {
  vpc_id         = data.aws_vpc.default.id
  default_for_az = true
  filter {
    name   = "availabilityZone"
    values = ["${var.aws_region}a"]
  }
}

module "exit_node" {
  source            = "../../../"
  region            = var.aws_region
  tailscale_api_key = var.tailscale_api_key
  name_prefix           = "ci-custom-vpc-${var.run_id}"
  vpc_id                = data.aws_vpc.default.id
  subnet_id             = data.aws_subnet.default.id
  tailscale_hostname    = "ci-custom-vpc-${var.run_id}"
  manage_tailscale_acl  = false
  device_join_timeout   = "600s"
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
output "security_group_id"  { value = module.exit_node.security_group_id }
output "expected_vpc_id"    { value = data.aws_vpc.default.id }
output "expected_subnet_id" { value = data.aws_subnet.default.id }
