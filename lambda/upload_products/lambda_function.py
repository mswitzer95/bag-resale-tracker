import os
import boto3
import logging
from common_lib import *
import pandas as pd
import s3fs


logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    """
    Runs the lambda, uploading products to S3.
    
    Args: 
        event (dict): Products to upload. Should be of structure:
            {
                "bucket_name": str,
                "object_name": str,
                "products": [
                    {
                        "brand_name": str,
                        "product_name": str,
                        "price": float,
                        "condition": str,
                        "product_family": str | None
                        "source": None
                    }
                ]
            }
            Additionally, "object_name" end in ".csv".
        context: Unused; any type
    Returns:
        dict: JSON of structure { "statusCode": int }
    """
    
    if (
        not isinstance(event, dict)
        or not all(key in event for key in [
            "bucket_name", "object_name", "products"])
        or not all(isinstance(value, str) for value in [
            event["bucket_name"], event["object_name"]])
        or not event["object_name"].endswith(".csv")
        or not isinstance(event["products"], list)
        or not all(isinstance(product, dict) for product in event["products"])
        or not all(
            (
                all(
                    key in product
                    for key in [
                        "brand_name", 
                        "product_name", 
                        "price", 
                        "condition", 
                        "product_family",
                        "source"])
                and all(
                    isinstance(product[key], value_type)
                    for (key, value_type) in [
                        ("brand_name", str),
                        ("product_name", str),
                        ("price", float),
                        ("condition", str),
                        ("product_family", (str, type(None))),
                        ("source", str)]
                )
            )
            for product in event["products"]
        )
    ):
        logger.error("Invalid args to lambda function.")
        return { "statusCode": 500 }
    
    products = event["products"]
    bucket_name = event["bucket_name"]
    object_name = event["object_name"]

    s3_client = boto3.client("s3")
    s3_resource = boto3.resource("s3")
    
    if bucket_name not in [
        bucket.get("Name") 
        for bucket in s3_client.list_buckets().get("Buckets")]:
        logger.error("Specified bucket does not exist.")
        return { "statusCode": 500 }
    bucket = s3_resource.Bucket(bucket_name)
    
    s3_object_url = f"s3://{bucket_name}/{object_name}"

    if object_name not in [obj.key for obj in bucket.objects.all()]:
        bucket.put_object(Key=object_name)
        old_dataframe = pd.DataFrame(columns=list(products[0].keys()))
    else:
        old_dataframe = pd.read_csv(s3_object_url)

    new_dataframe = pd.DataFrame(products)
    dataframe_to_upload = pd.concat([old_dataframe, new_dataframe])
    dataframe_to_upload.to_csv(s3_object_url, index=False)

    return { "statusCode": 200 }
