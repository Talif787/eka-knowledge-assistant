output "cluster_name" {
  description = "Name of the kind cluster."
  value       = kind_cluster.this.name
}

output "release_namespace" {
  description = "Namespace the chart was installed into."
  value       = helm_release.eka.namespace
}

output "port_forward_hint" {
  description = "Command to reach the API locally."
  value       = "kubectl port-forward -n ${var.namespace} svc/${var.release_name} 8000:8000"
}
