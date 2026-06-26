resource "aws_s3_bucket_website_configuration" "redirects" {
  bucket = aws_s3_bucket.redirects.id

  index_document {
    suffix = "index.html"
  }
}
