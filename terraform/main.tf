terraform {
  required_version = ">= 1.5.0"

  # Store Terraform state in S3
  backend "s3" {
    bucket       = "test-bucket-psardinha"
    key          = "decision-making/terraform/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Package the Python handler into a ZIP for Lambda.
data "archive_file" "lambda_package" {
  type        = "zip"
  source_file = "${path.module}/lambda/handler.py"
  output_path = "${path.module}/lambda-handler.zip"
}

# Lambda execution role.
resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Allow Lambda to write its output to CloudWatch Logs.
resource "aws_iam_role_policy" "lambda_executing" {
  name = "${var.function_name}-executing"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.function_name}:*"
      },
      {
        "Effect" : "Allow",
        "Action" : "secretsmanager:GetSecretValue",
        "Resource" : "arn:aws:secretsmanager:eu-central-1:801796542461:secret:process-optimization/github-dispatch-token-*"
    }]
  })
}

# Lambda function.
resource "aws_lambda_function" "handler" {
  function_name    = var.function_name
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      GITHUB_OWNER      = var.github_owner
      GITHUB_REPO       = var.github_repo
      GITHUB_EVENT_TYPE = var.github_event_type
      DATA_BUCKET       = var.data_bucket
      DATA_PREFIX       = var.data_prefix
      REGION            = var.aws_region
      SECRET_NAME       = var.secret_name
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_executing
  ]
}

# Enable delivery of S3 events to EventBridge for the existing bucket.
resource "aws_s3_bucket_notification" "eventbridge" {
  bucket      = var.data_bucket
  eventbridge = true
}

# Match creation or overwrite events for this exact object only.
resource "aws_cloudwatch_event_rule" "dataset_updated" {
  name        = "${var.function_name}-dataset-updated"
  description = "Trigger when orders_with_predicted_value.csv is created or overwritten"

  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]

    detail = {
      bucket = {
        name = [var.data_bucket]
      }

      object = {
        key = ["decision-making/incoming/orders_with_predicted_value.csv"]
      }
    }
  })

  depends_on = [
    aws_s3_bucket_notification.eventbridge
  ]
}

# Route matching events to Lambda.
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.dataset_updated.name
  target_id = "InvokeS3Handler"
  arn       = aws_lambda_function.handler.arn
}

# Allow EventBridge to invoke this Lambda.
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.handler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.dataset_updated.arn
}