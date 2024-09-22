This project scrapes resale handbag prices and dumps them to a flat file in an S3 bucket.


# Setup
## Set access key for TF:
export AWS_ACCESS_KEY_ID={AWS access key ID goes here}\
export AWS_SECRET_ACCESS_KEY={AWS secret access key goes here}

## Deploy:
terraform init\
terraform plan\
terraform apply

## To Destroy:
terraform destroy
