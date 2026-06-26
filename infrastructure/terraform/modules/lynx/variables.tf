##
# Generic tfscaffold Module Variables
##

variable "aws" {
  type = object({
    account_id   = string
    default_tags = optional(map(string), {})
    region       = string
  })
}

variable "module_parents" {
  type        = list(string)
  description = "List of parent module names"
  default     = []
}

variable "unique_ids" {
  type = object({
    # All marked as optional for consistency of code.
    # Whether each is optional depends on the module implementation.
    local   = optional(string, null)
    account = optional(string, null)
    global  = optional(string, null)
  })
}

variable "default_tags" {
  type        = map(string)
  description = "A map of default tags to apply to all taggable resources within the component"
  default     = {}
}

##
# Variables specific to this Module
##

variable "environment" {
  type        = string
  description = "Environment name (e.g. dev)"
}

variable "domain_root" {
  type        = string
  description = "Public app domain for this environment (e.g. lynx.example.com)"
}

variable "route53_zone_name" {
  type        = string
  description = "Route 53 hosted zone that contains the public app domain"
}

variable "alert_email" {
  type        = string
  description = "Email address for Lynx alert notifications"
}

variable "default_ttl" {
  type        = string
  description = "Default redirect TTL tag value"
  default     = "24h"
}

variable "default_ttl_expiration_days" {
  type        = number
  description = "Lifecycle expiration days for default TTL redirects"
  default     = 1
}

variable "extended_ttl" {
  type        = string
  description = "Extended redirect TTL tag value"
  default     = "7d"
}

variable "extended_ttl_expiration_days" {
  type        = number
  description = "Lifecycle expiration days for extended TTL redirects"
  default     = 7
}

variable "code_length" {
  type        = number
  description = "Generated short-code length"
  default     = 8
}

variable "max_url_length" {
  type        = number
  description = "Maximum accepted target URL length"
  default     = 2048
}

variable "lambda_runtime" {
  type        = string
  description = "Python runtime for regional Lambda functions"
  default     = "python3.13"
}

variable "edge_signer_runtime" {
  type        = string
  description = "Python runtime for the Lambda@Edge signer"
  default     = "python3.13"
}
