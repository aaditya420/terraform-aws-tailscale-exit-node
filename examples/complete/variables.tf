variable "tailscale_api_key" {
  type      = string
  sensitive = true
}

variable "region" {
  type    = string
  default = "eu-west-3"
}

variable "availability_zone" {
  type    = string
  default = ""
}

variable "adguard_password" {
  type      = string
  sensitive = true
  default   = null
}
