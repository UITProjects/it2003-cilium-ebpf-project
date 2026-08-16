locals {
  ssh_users = {
    for f in fileset("${path.module}/keys", "*.pub") :
    trimsuffix(f, ".pub") => trimspace(file("${path.module}/keys/${f}"))
  }
  node_name = "pve-master"
}

# Network
resource "proxmox_sdn_applier" "finalizer" {}

resource "proxmox_sdn_zone_simple" "it_2003_zone" {
  id         = "it2003"
  nodes      = [local.node_name]
  mtu        = 1500
  depends_on = [proxmox_sdn_applier.finalizer]
}

resource "proxmox_sdn_vnet" "it_2003_vnet" {
  id         = "it2003"
  zone       = proxmox_sdn_zone_simple.it_2003_zone.id
  depends_on = [proxmox_sdn_applier.finalizer]
}

resource "proxmox_sdn_subnet" "it_2003_subnet" {
  cidr       = "192.168.40.0/24"
  vnet       = proxmox_sdn_vnet.it_2003_vnet.id
  gateway    = "192.168.40.1"
  snat       = true
  depends_on = [proxmox_sdn_applier.finalizer]
}

resource "proxmox_sdn_applier" "commit" {
  depends_on = [
    proxmox_sdn_zone_simple.it_2003_zone,
    proxmox_sdn_vnet.it_2003_vnet,
    proxmox_sdn_subnet.it_2003_subnet,
  ]
}












resource "proxmox_download_file" "ubuntu_cloud_image" {
  content_type = "import"
  datastore_id = "local"
  node_name    = local.node_name
  url          = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
  file_name    = "noble-server-cloudimg-amd64.qcow2"
}
resource "proxmox_virtual_environment_vm" "it_2003_vm" {
  count     = 3
  name      = "it-2003-ubuntu2404-${count.index}"
  node_name = local.node_name
  tags      = ["course-project"]
  cpu {
    cores = 8
    type  = "x86-64-v2-AES"
  }
  stop_on_destroy = true
  initialization {
    ip_config {
      ipv4 {
        address = "192.168.40.${160 + count.index}/24"
        gateway = "192.168.40.1"
      }
    }
    user_account {
      username = "it2003"
      keys     = values(local.ssh_users)
    }
  }
  memory {
    dedicated = 4096
    floating  = 2048
  }
  disk {
    datastore_id = "local-lvm"
    import_from  = proxmox_download_file.ubuntu_cloud_image.id
    interface    = "virtio0"
    iothread     = true
    discard      = "on"
    size         = 120
  }
  network_device {
    bridge = proxmox_sdn_vnet.it_2003_vnet.id
  }
  depends_on = [
    proxmox_sdn_applier.commit
  ]
}