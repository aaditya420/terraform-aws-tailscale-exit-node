terraform {
  required_providers {
    aws       = { source = "hashicorp/aws",       version = "~> 5.0" }
    tailscale = { source = "tailscale/tailscale", version = "~> 0.16" }
    tls       = { source = "hashicorp/tls",       version = "~> 4.0" }
    random    = { source = "hashicorp/random",    version = "~> 3.0" }
  }
}

variable "tailscale_api_key" {
  type      = string
  sensitive = true
  default   = "dummy"
}

variable "device_join_timeout" {
  type    = string
  default = "300s"
}

# All inputs valid by default; tests override one variable at a time to trigger its validation.
module "exit_node" {
  source              = "../../../../"
  region              = "eu-west-3"
  tailscale_api_key   = var.tailscale_api_key
  device_join_timeout = var.device_join_timeout
}
