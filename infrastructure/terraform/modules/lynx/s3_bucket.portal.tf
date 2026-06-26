resource "aws_s3_bucket" "portal" {
  bucket = local.portal_bucket_name

  tags = merge(local.default_tags, {
    Name = local.portal_bucket_name
  })
}
