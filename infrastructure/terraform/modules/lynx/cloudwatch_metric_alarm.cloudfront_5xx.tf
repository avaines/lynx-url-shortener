resource "aws_cloudwatch_metric_alarm" "cloudfront_5xx" {
  provider = aws.us_east_1

  alarm_name          = "${local.resource_prefix}-cloudfront-5xx"
  alarm_description   = "CloudFront 5xx error rate is elevated for ${local.domain_name}."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.cloudfront_5xx_error_rate_alarm_threshold
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/CloudFront"
  metric_name = "5xxErrorRate"
  period      = 300
  statistic   = "Average"
  unit        = "Percent"

  dimensions = {
    DistributionId = aws_cloudfront_distribution.main.id
    Region         = "Global"
  }

  alarm_actions = [
    aws_sns_topic.alerts.arn,
  ]

  ok_actions = [
    aws_sns_topic.alerts.arn,
  ]

  tags = merge(local.default_tags, {
    Name = "${local.resource_prefix}-cloudfront-5xx"
  })
}
