resource "aws_lambda_function_url" "create_link" {
  function_name      = aws_lambda_function.create_link.function_name
  authorization_type = "AWS_IAM"
}
