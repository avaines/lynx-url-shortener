data "aws_iam_policy_document" "edge_signer" {
  statement {
    sid = "InvokeCreateLinkFunctionUrl"

    actions = [
      "lambda:InvokeFunctionUrl",
    ]

    resources = [
      aws_lambda_function.create_link.arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "lambda:FunctionUrlAuthType"
      values = [
        "AWS_IAM",
      ]
    }
  }

  statement {
    sid = "WriteEdgeLogs"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "arn:aws:logs:*:${var.aws.account_id}:*",
    ]
  }
}

resource "aws_iam_role_policy" "edge_signer" {
  name   = "${local.resource_prefix}-edge-signer"
  role   = aws_iam_role.edge_signer.id
  policy = data.aws_iam_policy_document.edge_signer.json
}
