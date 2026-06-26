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

variable "alias_domain_names" {
  type        = list(string)
  description = "Additional public app domains to alias to the same CloudFront distribution"
  default     = []
}

variable "route53_zone_name" {
  type        = string
  description = "Route 53 hosted zone that contains the public app domain"
}

variable "route53_zone_id" {
  type        = string
  description = "Route 53 hosted zone ID that contains the public app domain"
  default     = null
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

variable "cloudwatch_log_retention_days" {
  type        = number
  description = "CloudWatch Logs retention period for explicitly managed Lynx log groups"
  default     = 30

  validation {
    condition = contains(
      [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      var.cloudwatch_log_retention_days,
    )
    error_message = "cloudwatch_log_retention_days must be a valid CloudWatch Logs retention value."
  }
}

variable "create_link_error_alarm_threshold" {
  type        = number
  description = "Number of create-link Lambda runtime errors in one period before alarming"
  default     = 1
}

variable "create_link_throttle_alarm_threshold" {
  type        = number
  description = "Number of create-link Lambda throttles in one period before alarming"
  default     = 1
}

variable "cloudfront_5xx_error_rate_alarm_threshold" {
  type        = number
  description = "CloudFront 5xxErrorRate percentage threshold before alarming"
  default     = 5
}
