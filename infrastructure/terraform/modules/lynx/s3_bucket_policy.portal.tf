data "aws_iam_policy_document" "portal_bucket" {
  statement {
    sid = "AllowCloudFrontRead"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${aws_s3_bucket.portal.arn}/*",
    ]

    principals {
      type = "Service"
      identifiers = [
        "cloudfront.amazonaws.com",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values = [
        aws_cloudfront_distribution.main.arn,
      ]
    }
  }
}

resource "aws_s3_bucket_policy" "portal" {
  bucket = aws_s3_bucket.portal.id
  policy = data.aws_iam_policy_document.portal_bucket.json
}
