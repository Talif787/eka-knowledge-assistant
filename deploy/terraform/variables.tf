variable "cluster_name" {
  description = "Name of the local kind cluster."
  type        = string
  default     = "eka-local"
}

variable "release_name" {
  description = "Helm release name."
  type        = string
  default     = "eka"
}

variable "namespace" {
  description = "Namespace to install into."
  type        = string
  default     = "eka"
}
