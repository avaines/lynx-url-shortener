data "aws_iam_policy_document" "edge_signer_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type = "Service"
      identifiers = [
        "lambda.amazonaws.com",
        "edgelambda.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role" "edge_signer" {
  name               = local.edge_signer_role_name
  assume_role_policy = data.aws_iam_policy_document.edge_signer_assume_role.json

  tags = merge(local.default_tags, {
    Name = local.edge_signer_role_name
  })
}
