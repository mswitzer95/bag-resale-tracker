import os
import boto3
import logging
import re
import requests
from bs4 import BeautifulSoup
from datetime import date
from common_lib import PRODUCT_FAMILIES, CONDITIONS, Product, upload_products
from random import shuffle, choice
from time import sleep
from datetime import date


logger = logging.getLogger()
logger.setLevel("INFO")

BUCKET_NAME = os.environ.get("BUCKET_NAME")
OBJECT_NAME = os.environ.get("OBJECT_NAME")
LAMBDA_NAME = os.environ.get("UPLOAD_LAMBDA_NAME")
COLLECTIONS = [
    "speedy", 
    "neverfull", 
    "kelly", 
    "birkin",
    "hermes-constance",
    "chanel-double-flap-bags",
    "chanel-boy-bags",
    "chanel-deauville-bags",
    "christian-dior-lady-dior-bags",
    "christian-dior-saddle-bags",
    "gucci-jackie-bags",
    "gucci-marmont",
    "gucci-ophidia"
]
BASE_URL = "https://www.fashionphile.com/"
PRODUCT_FAMILY_REGEXS = {
    re.compile(
        ".*" + family.replace(" ", "(\s.*\s|\s)") + ".*", re.IGNORECASE
    ): family
    for family in PRODUCT_FAMILIES
}
FASHIONPHILE_CONDITION_TO_PRODUCT_CONDITION = {
    "Giftable": CONDITIONS[0],
    "New": CONDITIONS[0],
    "Excellent": CONDITIONS[1],
    "Shows Wear": CONDITIONS[2],
    "Worn": CONDITIONS[3],
    "Fair": CONDITIONS[4]
}


def lambda_handler(event, context):
    """
    Runs the lambda, scraping Fashionphile and saving to an S3 bucket.
    
    Args: 
        event: Unused; any type
        context: Unused; any type
    Returns: 
        dict: JSON of structure { "statusCode": int }
    """
    
    session = requests.Session()
    session.headers["User-Agent"] = "My User Agent 1.0"
    response = session.get(BASE_URL)
    if response.status_code != 200:
        logger.error(    
            f"Got {response.status_code} while requesting base URL.")
        return { "statusCode": 500 }
    
    products = []
    today = date.today().isoformat()
    shuffle(COLLECTIONS)
    for collection in COLLECTIONS:
        params = { 
            "categories": "handbags",
            "page": 0
        }
        more_to_fetch = True
        while more_to_fetch:
            params["page"] += 1
            response = session.get(f"{BASE_URL}l/{collection}", params=params)
            if response.status_code != 200:
                logger.error(
                    f"Got {response.status_code} while requesting " +
                    f"{collection} collection.")
                return { "statusCode": 500 }
        
            soup = BeautifulSoup(response.text, features="html.parser")

            pagination_tags = soup.find_all(
                "li", attrs={"class": "paginationWrapper pageLinkLi"})
            if not pagination_tags or len(pagination_tags) == 0:
                total_pages = 1
            else:
                total_pages = max([int(tag.text) for tag in pagination_tags])
            more_to_fetch = params["page"] < total_pages

            product_divs = soup.find_all("div", attrs={"class": "product"})
            for product_div in product_divs:
                brand_name_tag = product_div.find(
                    None, attrs={"itemprop": "brand"})
                brand_name = brand_name_tag.get("content")
            
                product_name_tag = product_div.find(
                    None, attrs={"class": "hitTitle"})
                product_name = product_name_tag.text
            
                price_tag = product_div.find(None, attrs={"itemprop": "price"})
                price_string = price_tag.text
                price_string = re.sub("\$|\,", "", price_string)
                price = float(price_string)

                condition_tag = product_div.find(
                    None, attrs={"class": "condition"})
                condition_string = condition_tag.text
                condition_string = condition_string.lstrip("Condition: ")
                condition = FASHIONPHILE_CONDITION_TO_PRODUCT_CONDITION.get(
                    condition_string)
            
                product_family = None
                for regex in PRODUCT_FAMILY_REGEXS.keys():
                    if regex.match(product_name):
                        product_family = PRODUCT_FAMILY_REGEXS.get(regex)
                        break

                product = Product(
                    brand_name=brand_name,
                    product_name=product_name,
                    price=price,
                    condition=condition,
                    product_family=product_family,
                    source="Fashionphile",
                    date=today)
                products.append(product)

            sleep(choice(range(1, 6)) / 10)

    upload_products(
        products=products,
        bucket_name=BUCKET_NAME,
        object_name=OBJECT_NAME,
        lambda_name=LAMBDA_NAME)
    
    logger.info(f"Uploaded {len(products)} products.")
    return { "statusCode": 200 }
