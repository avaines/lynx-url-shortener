resource "aws_s3_bucket" "redirects" {
  bucket = local.redirects_bucket_name

  tags = merge(local.default_tags, {
    Name = local.redirects_bucket_name
  })
}
