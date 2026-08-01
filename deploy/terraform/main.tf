# Provisions a local kind cluster and installs the eka Helm chart into it.
# Everything here is free: kind runs Kubernetes in Docker on your machine, and
# no cloud resources are created.
#
# The application image (eka:local) must exist in the cluster before the release
# can start, because values-local.yaml sets pullPolicy: Never. Because Terraform
# cannot build and load the image between creating the cluster and installing the
# chart in a single pass, apply in two steps the first time:
#
#   terraform apply -target=kind_cluster.this
#   (from the repo root) make image && kind load docker-image eka:local --name eka-local
#   terraform apply
#
# On later runs, a single "terraform apply" is enough as long as the image is
# loaded.

resource "kind_cluster" "this" {
  name           = var.cluster_name
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
    }
  }
}

provider "helm" {
  kubernetes {
    host                   = kind_cluster.this.endpoint
    client_certificate     = kind_cluster.this.client_certificate
    client_key             = kind_cluster.this.client_key
    cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
  }
}

provider "kubernetes" {
  host                   = kind_cluster.this.endpoint
  client_certificate     = kind_cluster.this.client_certificate
  client_key             = kind_cluster.this.client_key
  cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
}

resource "helm_release" "eka" {
  name             = var.release_name
  namespace        = var.namespace
  create_namespace = true

  chart  = "${path.module}/../helm/eka"
  values = [file("${path.module}/../helm/eka/values-local.yaml")]

  wait    = true
  timeout = 600

  depends_on = [kind_cluster.this]
}
