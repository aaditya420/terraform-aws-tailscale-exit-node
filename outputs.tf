output "instance_id" {
  description = "EC2 instance ID of the exit node."
  value       = aws_instance.tailscale_exit_node.id
}

output "instance_public_ip" {
  description = "Public IPv4 address of the exit node."
  value       = aws_instance.tailscale_exit_node.public_ip
}

output "instance_private_ip" {
  description = "Private IPv4 address of the exit node."
  value       = aws_instance.tailscale_exit_node.private_ip
}

output "tailscale_ip" {
  description = "Tailscale IPv4 address (100.x.x.x) of the exit node."
  value       = local.tailscale_device_ip
}

output "tailscale_device_id" {
  description = "Tailscale device ID."
  value       = local.tailscale_device_id_val
}

output "adguard_url" {
  description = "AdGuard Home web UI URL (accessible over Tailscale). Empty when adguard_enabled = false."
  value       = var.adguard_enabled ? "http://${local.tailscale_device_ip}:${var.adguard_web_port}" : ""
}

output "adguard_username" {
  description = "AdGuard Home admin username."
  value       = var.adguard_enabled ? var.adguard_username : null
}

output "adguard_password" {
  description = "AdGuard Home admin password (sensitive). Retrieve with: terraform output -json adguard_password"
  sensitive   = true
  value       = var.adguard_enabled ? local.adguard_password : null
}

output "ssh_command" {
  description = "SSH command to connect to the exit node."
  value       = "ssh -i ${var.name_prefix}-key.pem ubuntu@${aws_instance.tailscale_exit_node.public_ip}"
}

output "private_key_pem" {
  description = "PEM-encoded RSA private key for SSH (sensitive). Null when create_ssh_keypair = false."
  sensitive   = true
  value       = var.create_ssh_keypair ? tls_private_key.ssh[0].private_key_pem : null
}

output "security_group_id" {
  description = "ID of the security group attached to the exit node."
  value       = aws_security_group.tailscale.id
}

output "ami_id" {
  description = "AMI ID used to launch the instance."
  value       = local.ami_id
}
