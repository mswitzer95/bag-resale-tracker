# Lambda
resource "aws_lambda_function" "lambda" {
  depends_on       = [data.archive_file.lambda]
  filename         = "${var.function_name}.zip"
  function_name    = var.function_name
  role             = var.role_arn
  handler          = var.handler
  runtime          = var.runtime
  layers           = var.layers
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = var.timeout
  memory_size      = var.memory_size
  environment {
    variables = var.environment_variables
  }
}

# Zip
data "archive_file" "lambda" {
  type        = "zip"
  source_file = var.source_file
  output_path = "${var.function_name}.zip"
}

# CRON
resource "aws_cloudwatch_event_target" "lambda" {
  depends_on = [resource.aws_lambda_function.lambda]
  rule = var.cloudwatch_event_rule_name
  arn  = aws_lambda_function.lambda.arn
}
