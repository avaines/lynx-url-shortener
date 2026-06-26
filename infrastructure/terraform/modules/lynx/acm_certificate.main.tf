resource "aws_acm_certificate" "main" {
  provider = aws.us_east_1

  domain_name       = local.domain_name
  validation_method = "DNS"

  subject_alternative_names = local.alias_domain_names

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.default_tags, {
    Name = local.domain_name
  })
}
