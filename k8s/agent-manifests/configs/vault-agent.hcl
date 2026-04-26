auto_auth {
  method "kubernetes" {
    mount_path = "auth/kubernetes"
    config = {
      role = "scbe-agent"
    }
  }
}

cache {
  use_auto_auth_token = true
}

listener "tcp" {
  address = "127.0.0.1:8200"
  tls_disable = true
}

vault {
  address = "https://vault.service.consul:8200"
}

