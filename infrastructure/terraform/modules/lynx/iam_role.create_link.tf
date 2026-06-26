data "aws_iam_policy_document" "create_link_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type = "Service"
      identifiers = [
        "lambda.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role" "create_link" {
  name               = local.create_link_role_name
  assume_role_policy = data.aws_iam_policy_document.create_link_assume_role.json

  tags = merge(local.default_tags, {
    Name = local.create_link_role_name
  })
}
