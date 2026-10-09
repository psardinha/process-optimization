output "lambda_function_name" {
  description = "Name of the S3 event handler Lambda"
  value       = aws_lambda_function.handler.function_name
}

output "lambda_function_arn" {
  description = "ARN of the S3 event handler Lambda"
  value       = aws_lambda_function.handler.arn
}

output "eventbridge_rule_name" {
  description = "Name of the S3 event rule"
  value       = aws_cloudwatch_event_rule.dataset_updated.name
}
