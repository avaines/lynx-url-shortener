output "portal_url" {
  value = module.lynx.portal_url
}

output "api_url" {
  value = module.lynx.api_url
}

output "cloudfront_distribution_id" {
  value = module.lynx.cloudfront_distribution_id
}

output "cloudfront_distribution_domain_name" {
  value = module.lynx.cloudfront_distribution_domain_name
}

output "portal_bucket" {
  value = module.lynx.portal_bucket
}

output "redirect_bucket" {
  value = module.lynx.redirect_bucket
}

output "redirect_bucket_website_endpoint" {
  value = module.lynx.redirect_bucket_website_endpoint
}

output "alerts_topic_arn" {
  value = module.lynx.alerts_topic_arn
}

output "create_link_function_name" {
  value = module.lynx.create_link_function_name
}
