variable "vm_public_ip" {
  description = "Public IP of the target VM"
  type        = string
}

variable "vm_user" {
  description = "SSH user for the target VM"
  type        = string
  default     = "root"
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key file"
  type        = string
}
