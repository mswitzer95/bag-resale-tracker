import boto3
import pandas as pd
from botocore.exceptions import ClientError
from json import dumps, loads
import logging


logger = logging.getLogger()
logger.setLevel("INFO")


PRODUCT_FAMILIES = [
    "Speedy 20",
    "Speedy 25",
    "Speedy 30",
    "Speedy 35",
    "Speedy 40",
    "Neverfull MM",
    "Neverfull GM",
    "Kelly 20",
    "Kelly 25",
    "Kelly 28",
    "Kelly 32",
    "Kelly 35",
    "Birkin 25",
    "Birkin 30",
    "Birkin 35",
    "Birkin 40",
    "Constance 18",
    "Constance 24",
    "Double Flap",
    "Mini Boy Flap",
    "Small Boy Flap",
    "Medium Boy Flap",
    "Small Deauville",
    "Medium Deauville",
    "Large Deauville",
    "Mini Lady Dior",
    "Small Lady Dior",
    "Medium Lady Dior",
    "Large Lady Dior",
    "Saddle Bag",
    "Mini Jackie",
    "Small Jackie",
    "Medium Jackie",
    "Large Jackie",
    "Mini Marmont",
    "Small Marmont",
    "Medium Marmont",
    "Ophidia"
]

CONDITIONS = [
    "1 - New",
    "2 - Excellent",
    "3 - Shows Wear",
    "4 - Worn",
    "5 - Fair"
]


class Product:
    """
    A product scraped from a data source.
    
    Attributes:
        brand_name (str): The brand name of the product
        product_name (str): The name of the product
        price (float): The price of the product
        condition (str): The condition of the product. Must in the 
            "CONDITIONS" list defined in this package.
        product_family (str): The product family of the product. Must be in 
            the "PRODUCT_FAMILIES" list defined in this package.
        source (str): The source where the product is listed for sale.
        date (str): A string representation of the date the product was 
            scraped.
    """
    
    def __init__(
            self, 
            brand_name: str, 
            product_name: str,
            price: float,
            condition: str,
            product_family: str | None,
            source: str,
            date: str) -> None:
        """
        Constructor
        Args:
            brand_name (str): The brand name of the product
            product_name (str): The name of the product
            price (float): The price of the product
            condition (str): The condition of the product. Must in the 
                "CONDITIONS" list defined in this package.
            product_family (str): The product family of the product. Must be 
                in the "PRODUCT_FAMILIES" list defined in this package.
            source (str): The source where the product is listed for sale.
            date (str): A string representation of the date the product was 
                scraped.
        Returns: None
        """

        if (
            not all(
                isinstance(arg, str)
                for arg in [brand_name, product_name, condition, source, date])
            or not condition in CONDITIONS
            or not isinstance(price, float)
            or not (
                isinstance(product_family, type(None))
                or product_family in PRODUCT_FAMILIES)):
            logger.error("Invalid args while instantiating Product.")
            raise Exception("Invalid args.")
        
        self.brand_name = brand_name
        self.product_name = product_name
        self.price = price
        self.condition = condition
        self.product_family = product_family
        self.source = source
        self.date = date


def upload_products(
        products: list,
        bucket_name: str,
        object_name: str,
        lambda_name: str) -> None:
    """
    Invokes the lambda to upload products to a CSV file in an S3 bucket.
    
    Args:
        products (list(Product)): The products to upload. Must be non-empty
        bucket_name (str): The name of the bucket to upload to
        object_name (str): The name of the CSV file to upload to. Must be a 
            valid CSV file name.
        lambda_name (str): The name of the lambda to invoke to upload.
    Returns: None
    """
    
    if (
        not isinstance(products, list)
        or not all(isinstance(product, Product) for product in products)
        or not len(products) > 0
        or not all(
            isinstance(arg, str) 
            for arg in [bucket_name, object_name, lambda_name])
        or not object_name.endswith(".csv")):
        raise Exception("Invalid args.")
    
    client = boto3.client("lambda")
    
    try:
        client.get_function(FunctionName=lambda_name)
    except ClientError:
        raise Exception("Function not found.")

    payload = dumps(
        {
            "bucket_name": bucket_name,
            "object_name": object_name,
            "products": [product.__dict__ for product in products]
        }
    )
    
    response = client.invoke(FunctionName=lambda_name, Payload=payload)
    logger.info(response["Payload"].read().decode("utf-8"))
    return
