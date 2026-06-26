data "aws_iam_policy_document" "redirects_bucket" {
  statement {
    sid = "AllowPublicRedirectObjectRead"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${aws_s3_bucket.redirects.arn}/*",
    ]

    principals {
      type = "*"
      identifiers = [
        "*",
      ]
    }
  }
}

resource "aws_s3_bucket_policy" "redirects" {
  bucket = aws_s3_bucket.redirects.id
  policy = data.aws_iam_policy_document.redirects_bucket.json

  depends_on = [
    aws_s3_bucket_public_access_block.redirects,
  ]
}
