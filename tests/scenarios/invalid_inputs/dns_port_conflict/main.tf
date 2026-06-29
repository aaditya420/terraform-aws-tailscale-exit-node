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

module "exit_node" {
  source            = "../../../../"
  region            = "eu-west-3"
  tailscale_api_key = var.tailscale_api_key
  adguard_web_port  = 53
}
