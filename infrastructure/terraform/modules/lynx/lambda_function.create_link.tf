resource "aws_lambda_function" "create_link" {
  function_name    = local.create_link_function_name
  filename         = data.archive_file.create_link.output_path
  source_code_hash = data.archive_file.create_link.output_base64sha256
  role             = aws_iam_role.create_link.arn
  handler          = "create_link.handler.lambda_handler"
  runtime          = var.lambda_runtime
  memory_size      = 128
  timeout          = 10

  environment {
    variables = {
      ALERTS_TOPIC_ARN     = aws_sns_topic.alerts.arn
      CODE_LENGTH          = tostring(var.code_length)
      DEFAULT_TTL          = var.default_ttl
      ENVIRONMENT          = var.environment
      MAX_URL_LENGTH       = tostring(var.max_url_length)
      PUBLIC_BASE_URL      = local.public_base_url
      REDIRECT_BUCKET_NAME = aws_s3_bucket.redirects.id
    }
  }

  tags = merge(local.default_tags, {
    Name = local.create_link_function_name
  })
}
