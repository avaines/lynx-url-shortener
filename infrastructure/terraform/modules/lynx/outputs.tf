output "portal_url" {
  value = local.public_base_url
}

output "api_url" {
  value = "${local.public_base_url}/api/links"
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.main.id
}

output "cloudfront_distribution_domain_name" {
  value = aws_cloudfront_distribution.main.domain_name
}

output "portal_bucket" {
  value = aws_s3_bucket.portal.id
}

output "redirect_bucket" {
  value = aws_s3_bucket.redirects.id
}

output "redirect_bucket_website_endpoint" {
  value = aws_s3_bucket_website_configuration.redirects.website_endpoint
}

output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "create_link_function_name" {
  value = aws_lambda_function.create_link.function_name
}

output "create_link_function_url" {
  value     = aws_lambda_function_url.create_link.function_url
  sensitive = true
}

output "edge_signer_function_qualified_arn" {
  value = aws_lambda_function.edge_signer.qualified_arn
}

output "acm_certificate_arn" {
  value = aws_acm_certificate.main.arn
}
