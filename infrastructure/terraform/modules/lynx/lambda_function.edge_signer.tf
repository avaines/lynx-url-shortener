resource "aws_lambda_function" "edge_signer" {
  provider = aws.us_east_1

  function_name    = local.edge_signer_function_name
  filename         = data.archive_file.edge_signer.output_path
  source_code_hash = data.archive_file.edge_signer.output_base64sha256
  role             = aws_iam_role.edge_signer.arn
  handler          = "edge_signer.handler.lambda_handler"
  runtime          = var.edge_signer_runtime
  memory_size      = 128
  timeout          = 5
  publish          = true

  tags = merge(local.default_tags, {
    Name = local.edge_signer_function_name
  })
}
