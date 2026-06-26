resource "aws_s3_bucket_lifecycle_configuration" "main" {
  count  = (var.lifecycle_expiration_days != null || var.lifecycle_noncurrent_expiration_days != null) ? 1 : 0
  bucket = aws_s3_bucket.main.id

  dynamic "rule" {
    for_each = var.lifecycle_expiration_days != null ? [1] : []
    content {
      id     = "expire-objects"
      status = "Enabled"
      filter {}
      expiration {
        days = var.lifecycle_expiration_days
      }
    }
  }

  dynamic "rule" {
    for_each = var.lifecycle_noncurrent_expiration_days != null ? [1] : []
    content {
      id     = "expire-noncurrent-versions"
      status = "Enabled"
      filter {}
      noncurrent_version_expiration {
        noncurrent_days = var.lifecycle_noncurrent_expiration_days
      }
    }
  }
}
