variable "function_name" {
  description = "The name of the Lambda function in AWS."
  type        = string
}

variable "role_arn" {
  description = "The ARN of the IAM role for the Lambda function to assume."
  type        = string
}

variable "handler" {
  description = "The handler of the Lambda function."
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "runtime" {
  description = "The runtime of the Lambda function."
  type        = string
  default     = "python3.10"
}

variable "layers" {
  description = "The ARNs of the Lambda layers the Lambda function should have access to."
  type        = list(string)
}

variable "timeout" {
  description = "The execution timeout (in seconds) of the Lambda function."
  type        = number
  default     = 180
}

variable "memory_size" {
  description = "The memory size (in MB) of the Lambda function."
  type        = number
  default     = 512
}

variable "environment_variables" {
  description = "The environment variables for the Lambda function."
  type        = map(any)
}

variable "source_file" {
  description = "The path to the Lambda source code."
  type        = string
}

variable "cloudwatch_event_rule_name" {
  description = "The name of the Cloudwatch Event Rule to attach to the Lambda."
  type        = string
}

variable "cloudwatch_event_rule_arn" {
  description = "The ARN of the CloudWatch Event Rule to attach to the Lambda."
  type        = string
}