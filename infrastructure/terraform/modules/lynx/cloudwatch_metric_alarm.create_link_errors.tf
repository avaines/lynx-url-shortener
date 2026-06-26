resource "aws_cloudwatch_metric_alarm" "create_link_errors" {
  alarm_name          = "${local.resource_prefix}-create-link-errors"
  alarm_description   = "Create-link Lambda runtime errors are occurring."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = var.create_link_error_alarm_threshold
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
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
    Name = "${local.resource_prefix}-create-link-errors"
  })
}
