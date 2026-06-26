resource "aws_s3_bucket" "main" {
  bucket = local.unique_id_global

  tags = merge(local.default_tags, {
    Name = local.unique_id_global
  })
}
