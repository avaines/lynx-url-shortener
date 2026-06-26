data "aws_route53_zone" "main" {
  name         = "${local.route53_zone_name}."
  private_zone = false
}
