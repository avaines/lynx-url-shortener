data "aws_iam_policy_document" "alerts_topic" {
  statement {
    sid = "AllowCreateLinkPublish"

    actions = [
      "SNS:Publish",
    ]

    resources = [
      aws_sns_topic.alerts.arn,
    ]

    principals {
      type = "AWS"
      identifiers = [
        aws_iam_role.create_link.arn,
      ]
    }
  }

  statement {
    sid = "AllowCloudWatchAlarmPublish"

    actions = [
      "SNS:Publish",
    ]

    resources = [
      aws_sns_topic.alerts.arn,
    ]

    principals {
      type = "Service"
      identifiers = [
        "cloudwatch.amazonaws.com",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"
      values = [
        var.aws.account_id,
      ]
    }
  }
}

resource "aws_sns_topic_policy" "alerts" {
  arn    = aws_sns_topic.alerts.arn
  policy = data.aws_iam_policy_document.alerts_topic.json
}
