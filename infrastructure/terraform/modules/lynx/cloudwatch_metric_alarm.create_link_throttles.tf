resource "aws_cloudwatch_metric_alarm" "create_link_throttles" {
  alarm_name          = "${local.resource_prefix}-create-link-throttles"
  alarm_description   = "Create-link Lambda throttles are occurring."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = var.create_link_throttle_alarm_threshold
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/Lambda"
  metric_name = "Throttles"
  period      = 60
  statistic   = "Sum"

  dimensions = {
    FunctionName = aws_lambda_function.create_link.function_name
  }

  alarm_actions = [
    aws_sns_topic.alerts.arn,
  ]

  ok_actions = [
    aws_sns_topic.alerts.arn,
  ]

  tags = merge(local.default_tags, {
    Name = "${local.resource_prefix}-create-link-throttles"
  })
}
