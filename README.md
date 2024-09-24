This project scrapes resale handbag prices and dumps them to a flat file in an S3 bucket. The data in this bucket is to be accessed by Power BI to create dashboards and visualizations that support business logic (outside the scope of this repo). The broad application has the following architecture:\
![architectural diagram](./diagram.png)


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
