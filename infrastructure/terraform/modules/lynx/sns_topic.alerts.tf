resource "aws_sns_topic" "alerts" {
  name = "${local.resource_prefix}-alerts"

  tags = merge(local.default_tags, {
    Name = "${local.resource_prefix}-alerts"
  })
}
