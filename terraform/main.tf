terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}


provider "aws" {
  region  = "us-east-1"
}


# S3 Bucket
resource "aws_s3_bucket" "csv_bucket" {
  bucket = "bag-resale-tracker-bucket"
}

resource "aws_s3_bucket_public_access_block" "csv_bucket" {
  bucket = aws_s3_bucket.csv_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

data "aws_iam_policy_document" "csv_bucket" {
  statement {
    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:GetObject"]

    resources = [
      aws_s3_bucket.csv_bucket.arn,
      "${aws_s3_bucket.csv_bucket.arn}/*",
    ]
  }
}

resource "aws_s3_bucket_policy" "csv_bucket" {
  depends_on = [aws_s3_bucket_public_access_block.csv_bucket]
  bucket = aws_s3_bucket.csv_bucket.id
  policy = data.aws_iam_policy_document.csv_bucket.json
}


# IAM role for all lambdas
data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "s3_full_access" {
  statement {
    effect    = "Allow"
    actions   = ["s3:*"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "lambda_full_access" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:*"]
    resources = ["*"]
  }
}

resource "aws_iam_role" "bag_resale_tracker_lambda_role" {
  name               = "bag_resale_tracker_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  inline_policy {
    name   = "s3_full_access"
    policy = data.aws_iam_policy_document.s3_full_access.json
  }
  inline_policy {
    name   = "lambda_full_access"
    policy = data.aws_iam_policy_document.lambda_full_access.json
  }
}


# Shared lambda layer
resource "null_resource" "make_python_dir" {
    provisioner "local-exec" {
      command = <<EOT
        mkdir -p ./lambda_layer/python
      EOT
    }
    triggers = {
      timestamp = timestamp()
    }
}

resource "null_resource" "install_dependencies" {
  depends_on = [null_resource.make_python_dir]
  provisioner "local-exec" {
    command = <<EOT
      rm -rf ./lambda_layer/python
      mkdir ./lambda_layer/python
      cp ../lambda/layer/common_lib.py ./lambda_layer/python
      pip install -r ../lambda/requirements.txt -t ./lambda_layer/python
EOT
  }
  triggers = {
    sha1 = sha1(
      join("", concat(
        [for f in fileset("./lambda_layer/python", "*") : filesha1("./lambda_layer/python/${f}")],
        [filesha1("../lambda/requirements.txt")],
        [filesha1("../lambda/layer/common_lib.py")]
      ))
    )
  }
}

data "archive_file" "layers_zip" {
  depends_on  = [null_resource.install_dependencies]
  type        = "zip"
  source_dir  = "./lambda_layer"
  output_path = "lambda_layer.zip"
}

resource "aws_s3_bucket" "layer_bucket" {
  bucket = "bag-resale-tracker-lambda-layer-bucket"
}

resource "aws_s3_object" "layer_object" {
  depends_on    = [data.archive_file.layers_zip]
  bucket        = aws_s3_bucket.layer_bucket.bucket
  key           = "bag-resale-tracker-lambda-layer.zip"
  source        = "lambda_layer.zip"
  source_hash   = join(
    "", concat(
      [filemd5("../lambda/layer/common_lib.py")],
      [filemd5("../lambda/requirements.txt")]
    )
  )
}

resource "aws_lambda_layer_version" "bag_resale_tracker_lambda_layer" {
  depends_on          = [aws_s3_object.layer_object]
  s3_bucket           = aws_s3_object.layer_object.bucket
  s3_key              = aws_s3_object.layer_object.key
  layer_name          = "bag-resale_tracker_lambda-layer"
  compatible_runtimes = ["python3.10"]
  source_code_hash    = join(
    "", concat(
      [filemd5("../lambda/layer/common_lib.py")],
      [filemd5("../lambda/requirements.txt")]
    )
  )
}


# Resources for Fashionphile lambda
data "archive_file" "fashionphile_lambda" {
  type        = "zip"
  source_file = "../lambda/fashionphile/lambda_function.py"
  output_path = "fashionphile_lambda.zip"
}

resource "aws_lambda_function" "fashionphile_lambda" {
  depends_on       = [data.archive_file.fashionphile_lambda]
  filename         = "fashionphile_lambda.zip"
  function_name    = "fashionphile_lambda"
  role             = aws_iam_role.bag_resale_tracker_lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.10"
  layers           = [aws_lambda_layer_version.bag_resale_tracker_lambda_layer.arn]
  source_code_hash = data.archive_file.fashionphile_lambda.output_base64sha256
  timeout          = 120
  memory_size      = 512
  environment {
    variables = {
      BUCKET_NAME = "${aws_s3_bucket.csv_bucket.bucket}"
      OBJECT_NAME = "bag-resale-tracker.csv"
      UPLOAD_LAMBDA_NAME = "${aws_lambda_function.upload_products_lambda.function_name}"
    }
  }
}

resource "aws_cloudwatch_event_rule" "fashionphile_lambda_schedule" {
  name                = "fashionphile-lambda-schedule"
  schedule_expression = "cron(0 0 ? * * *)"
}

resource "aws_cloudwatch_event_target" "fashionphile_lambda_target" {
  rule = aws_cloudwatch_event_rule.fashionphile_lambda_schedule.name
  arn  = aws_lambda_function.fashionphile_lambda.arn
}


# Resources for upload products lambda
data "archive_file" "upload_products_lambda" {
  type        = "zip"
  source_file = "../lambda/upload_products/lambda_function.py"
  output_path = "upload_products_lambda.zip"
}

resource "aws_lambda_function" "upload_products_lambda" {
  depends_on       = [data.archive_file.upload_products_lambda]
  filename         = "upload_products_lambda.zip"
  function_name    = "upload_products_lambda"
  role             = aws_iam_role.bag_resale_tracker_lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.10"
  layers           = [aws_lambda_layer_version.bag_resale_tracker_lambda_layer.arn]
  source_code_hash = data.archive_file.upload_products_lambda.output_base64sha256
  timeout          = 60
  memory_size      = 2048
}


# Resources for Luxe du Jour lambda
data "archive_file" "luxe_du_jour_lambda" {
  type        = "zip"
  source_file = "../lambda/luxe_du_jour/lambda_function.py"
  output_path = "luxe_du_jour_lambda.zip"
}

resource "aws_lambda_function" "luxe_du_jour_lambda" {
  depends_on       = [data.archive_file.luxe_du_jour_lambda]
  filename         = "luxe_du_jour_lambda.zip"
  function_name    = "luxe_du_jour_lambda"
  role             = aws_iam_role.bag_resale_tracker_lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.10"
  layers           = [aws_lambda_layer_version.bag_resale_tracker_lambda_layer.arn]
  source_code_hash = data.archive_file.luxe_du_jour_lambda.output_base64sha256
  timeout          = 120
  memory_size      = 512
  environment {
    variables = {
      BUCKET_NAME = "${aws_s3_bucket.csv_bucket.bucket}"
      OBJECT_NAME = "bag-resale-tracker.csv"
      UPLOAD_LAMBDA_NAME = "${aws_lambda_function.upload_products_lambda.function_name}"
    }
  }
}

resource "aws_cloudwatch_event_rule" "luxe_du_jour_lambda_schedule" {
  name                = "luxe-du-jour-lambda-schedule"
  schedule_expression = "cron(0 0 ? * * *)"
}

resource "aws_cloudwatch_event_target" "luxe_du_jour_lambda_target" {
  rule = aws_cloudwatch_event_rule.luxe_du_jour_lambda_schedule.name
  arn  = aws_lambda_function.luxe_du_jour_lambda.arn
}

