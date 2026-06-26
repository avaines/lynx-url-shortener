resource "aws_cloudwatch_log_group" "edge_signer" {
  provider = aws.us_east_1

  name              = "/aws/lambda/${local.edge_signer_function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(local.default_tags, {
    Name = "/aws/lambda/${local.edge_signer_function_name}"
  })
}
