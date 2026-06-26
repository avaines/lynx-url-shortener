module "lynx" {
  source = "../../modules/lynx"

  aws = local.aws

  unique_ids = {
    local   = "${local.unique_id}-lynx"
    account = "${local.unique_id_account}-lynx"
    global  = "${local.unique_id_global}-lynx"
  }

  default_tags   = local.default_tags
  module_parents = ["prod"]

  environment = var.environment
  domain_root = var.domain_root
  alert_email = var.alert_email

}
