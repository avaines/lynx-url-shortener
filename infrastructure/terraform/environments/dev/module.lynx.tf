module "lynx" {
  source = "../../modules/lynx"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  aws = local.aws

  unique_ids = {
    local   = "${local.unique_id}-lynx"
    account = "${local.unique_id_account}-lynx"
    global  = "${local.unique_id_global}-lynx"
  }

  default_tags   = local.default_tags
  module_parents = ["dev"]

  environment       = var.environment
  domain_root       = var.domain_root
  route53_zone_name = var.route53_zone_name
  alert_email       = var.alert_email

}
