resource "aws_s3_bucket_server_side_encryption_configuration" "redirects" {
  bucket = aws_s3_bucket.redirects.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
