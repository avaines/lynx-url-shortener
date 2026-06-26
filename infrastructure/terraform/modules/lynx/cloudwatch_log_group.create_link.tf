resource "aws_cloudwatch_log_group" "create_link" {
  name              = "/aws/lambda/${local.create_link_function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(local.default_tags, {
    Name = "/aws/lambda/${local.create_link_function_name}"
  })
}
