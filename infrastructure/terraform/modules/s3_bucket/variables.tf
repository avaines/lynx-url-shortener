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

variable "enable_versioning" {
  type    = bool
  default = false
}

variable "lifecycle_expiration_days" {
  type    = number
  default = null
}

variable "lifecycle_noncurrent_expiration_days" {
  type    = number
  default = null
}
