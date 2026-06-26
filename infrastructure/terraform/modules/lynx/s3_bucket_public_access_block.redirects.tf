resource "aws_s3_bucket_public_access_block" "redirects" {
  bucket                  = aws_s3_bucket.redirects.id
  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false
}
