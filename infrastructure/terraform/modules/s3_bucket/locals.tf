locals {
  module = "s3_bucket"

  unique_id         = var.unique_ids["local"]
  unique_id_account = var.unique_ids["account"]
  unique_id_global  = var.unique_ids["global"]

  default_tags = merge(
    var.default_tags,
    {
      "Name"      = local.unique_id,
      "tf:module" = local.module
    },
    length(var.module_parents) == 0 ? {} : {
      "tf:module:parents" = join(":", var.module_parents)
    }
  )
}
