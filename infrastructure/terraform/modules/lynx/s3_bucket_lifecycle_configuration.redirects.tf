resource "aws_s3_bucket_lifecycle_configuration" "redirects" {
  bucket = aws_s3_bucket.redirects.id

  rule {
    id     = "expire-${var.default_ttl}"
    status = "Enabled"

    filter {
      tag {
        key   = "ttl"
        value = var.default_ttl
      }
    }

    expiration {
      days = var.default_ttl_expiration_days
    }
  }

  rule {
    id     = "expire-${var.extended_ttl}"
    status = "Enabled"

    filter {
      tag {
        key   = "ttl"
        value = var.extended_ttl
      }
    }

    expiration {
      days = var.extended_ttl_expiration_days
    }
  }
}
