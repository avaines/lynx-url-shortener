resource "aws_acm_certificate_validation" "main" {
  provider = aws.us_east_1

  certificate_arn = aws_acm_certificate.main.arn
  validation_record_fqdns = [
    for record in aws_route53_record.acm_validation : record.fqdn
  ]
}
