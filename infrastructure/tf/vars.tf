variable "proxmox_password" {
  type      = string
  sensitive = true
}
variable "proxmox_endpoint" {
  description = "ENDPOINT"
  sensitive   = true
  type        = string
}
variable "proxmox_username" {
  type      = string
  sensitive = true
}