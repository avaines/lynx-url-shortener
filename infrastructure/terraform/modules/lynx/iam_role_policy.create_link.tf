data "aws_iam_policy_document" "create_link" {
  statement {
    sid = "WriteRedirectObjects"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:PutObjectTagging",
    ]

    resources = [
      "${aws_s3_bucket.redirects.arn}/l/*",
    ]
  }

  statement {
    sid = "CheckRedirectObjectExistence"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.redirects.arn,
    ]
  }

  statement {
    sid = "PublishAlerts"

    actions = [
      "sns:Publish",
    ]

    resources = [
      aws_sns_topic.alerts.arn,
    ]
  }

  statement {
    sid = "WriteLogs"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "arn:aws:logs:${var.aws.region}:${var.aws.account_id}:*",
    ]
  }
}

resource "aws_iam_role_policy" "create_link" {
  name   = "${local.resource_prefix}-create-link"
  role   = aws_iam_role.create_link.id
  policy = data.aws_iam_policy_document.create_link.json
}
