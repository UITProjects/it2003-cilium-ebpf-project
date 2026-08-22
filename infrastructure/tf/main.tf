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

// Firewall


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
    cores = 4
    type  = "host"
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
    dedicated = 6144
    floating  = 6144
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
    bridge   = proxmox_sdn_vnet.it_2003_vnet.id
    firewall = true
  }
  depends_on = [
    proxmox_sdn_applier.commit
  ]
}


resource "proxmox_virtual_environment_vm" "it_2003_vpn_vm" {
  name      = "it-2003-vpn-server"
  node_name = local.node_name
  tags      = ["course-project"]
  cpu {
    cores = 2
  }
  stop_on_destroy = true
  initialization {
    ip_config {
      ipv4 {
        address = "192.168.40.10/24"
        gateway = "192.168.40.1"
      }
    }
    ip_config {
      ipv4 {
        address = "192.168.1.179/24"
        gateway = "192.168.1.1"
      }
    }
    user_account {
      username = "it2003"
      keys     = values(local.ssh_users)
    }
  }
  memory {
    dedicated = 2048
    floating  = 1024
  }
  disk {
    datastore_id = "local-lvm"
    import_from  = proxmox_download_file.ubuntu_cloud_image.id
    interface    = "virtio0"
    iothread     = true
    discard      = "on"
    size         = 30
  }
  network_device {
    bridge   = proxmox_sdn_vnet.it_2003_vnet.id
    firewall = true
  }
  network_device {
    bridge   = "vmbr0"
    firewall = true
  }
  depends_on = [
    proxmox_sdn_applier.commit
  ]
}


// Firewall

resource "proxmox_virtual_environment_firewall_options" "it_2003_fw_opts" {
  count         = 3
  node_name     = proxmox_virtual_environment_vm.it_2003_vm[count.index].node_name
  vm_id         = proxmox_virtual_environment_vm.it_2003_vm[count.index].vm_id
  input_policy  = "ACCEPT"
  output_policy = "ACCEPT"
  enabled       = true
}

resource "proxmox_virtual_environment_firewall_rules" "it_2003_outbound" {
  count = 3

  depends_on = [
    proxmox_virtual_environment_vm.it_2003_vm,
  ]

  node_name = proxmox_virtual_environment_vm.it_2003_vm[count.index].node_name
  vm_id     = proxmox_virtual_environment_vm.it_2003_vm[count.index].vm_id

  # --- Deny all other outbound traffic to the LAN subnet ---
  rule {
    type    = "out"
    action  = "DROP"
    comment = "Deny ALL outbound to LAN subnet"
    dest    = "192.168.1.0/24"
    log     = "warning"
  }
}