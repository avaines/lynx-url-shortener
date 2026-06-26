resource "aws_cloudfront_origin_access_control" "portal" {
  name                              = "${local.resource_prefix}-portal"
  description                       = "Lynx portal S3 origin access"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}
