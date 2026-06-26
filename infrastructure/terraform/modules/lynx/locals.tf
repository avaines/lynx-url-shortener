locals {
  module = "lynx"

  unique_id         = var.unique_ids["local"]
  unique_id_account = var.unique_ids["account"]
  unique_id_global  = var.unique_ids["global"]

  domain_name       = trimsuffix(var.domain_root, ".")
  route53_zone_name = trimsuffix(var.route53_zone_name, ".")
  public_base_url   = "https://${local.domain_name}"

  resource_prefix        = lower(replace(local.unique_id_account, "_", "-"))
  global_resource_prefix = lower(replace(local.unique_id_global, "_", "-"))

  portal_bucket_name    = substr("${local.global_resource_prefix}-portal", 0, 63)
  redirects_bucket_name = substr("${local.global_resource_prefix}-redirects", 0, 63)

  create_link_function_name  = substr("${local.resource_prefix}-create-link", 0, 64)
  edge_signer_function_name  = substr("${local.global_resource_prefix}-edge-signer", 0, 64)
  create_link_role_name      = substr("${local.resource_prefix}-create-link", 0, 64)
  edge_signer_role_name      = substr("${local.global_resource_prefix}-edge-signer", 0, 64)
  cloudfront_distribution_id = "cloudfront"

  portal_origin_id    = "portal-s3"
  api_origin_id       = "create-link-function-url"
  redirects_origin_id = "redirects-s3-website"

  lambdas_path              = abspath("${path.module}/../../../lambdas")
  create_link_archive_path  = "${path.root}/.terraform/${local.resource_prefix}-create-link.zip"
  edge_signer_archive_path  = "${path.root}/.terraform/${local.resource_prefix}-edge-signer.zip"
  create_link_function_host = trimsuffix(trimprefix(aws_lambda_function_url.create_link.function_url, "https://"), "/")

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
