terraform {
  required_version = ">= 1.5"
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

resource "random_password" "db_password" {
  length  = 24
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "grafana_password" {
  length  = 24
  special = false
}

locals {
  project_name      = "sentinel"
  deploy_user       = "sentinel"
  deploy_group      = "sentinel"
  app_dir           = "/opt/sentinel"
  docker_compose_ver = "2.27.0"
}

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
  description = "Path to SSH private key for VM access"
  type        = string
}

output "connection_info" {
  value = {
    ansible_user          = var.vm_user
    ansible_host          = var.vm_public_ip
    ansible_ssh_private_key_file = var.ssh_private_key_path
    app_directory         = local.app_dir
    gateway_url           = "http://${var.vm_public_ip}"
    grafana_url           = "http://${var.vm_public_ip}/grafana/"
    prometheus_url        = "http://${var.vm_public_ip}/prometheus/"
    jaeger_url            = "http://${var.vm_public_ip}/jaeger/"
  }
}

output "generated_secrets" {
  sensitive = true
  value = {
    database_password   = random_password.db_password.result
    jwt_secret_key      = random_password.jwt_secret.result
    grafana_password    = random_password.grafana_password.result
  }
}
