import os
import boto3
import logging
import requests
from bs4 import BeautifulSoup
from json import dumps, loads
from common_lib import PRODUCT_FAMILIES, CONDITIONS, Product, upload_products
from random import shuffle, sample, choice
import re
from time import sleep
from datetime import date


logger = logging.getLogger()
logger.setLevel("INFO")

BUCKET_NAME = os.environ.get("BUCKET_NAME")
OBJECT_NAME = os.environ.get("OBJECT_NAME")
LAMBDA_NAME = os.environ.get("UPLOAD_LAMBDA_NAME")

BASE_URL = "https://ldj.com/"
BRAND_QUERY_COMBOS = [
    ("Louis Vuitton", "Speedy"),
    ("Louis Vuitton", "Neverfull"),
    ("Hermes", "Kelly"),
    ("Hermes", "Birkin"),
    ("Hermes", "Constance"),
    ("Chanel", "Classic Flap"),
    ("Chanel", "Boy Bag"),
    ("Chanel", "Deauville"),
    ("Dior", "Lady Dior"),
    ("Dior", "Saddle"),
    ("Gucci", "Jackie"),
    ("Gucci", "Marmont"),
    ("Gucci", "Ophidia"),
]

PRODUCT_FAMILY_REGEXS = {
    re.compile(
        "".join([f"(?=.*{phrase})" for phrase in family.split(" ")]),
        re.IGNORECASE
    ): family
    for family in [
        f for f in PRODUCT_FAMILIES
        if f not in [
            "Double Flap", 
            "Mini Boy Flap",
            "Small Boy Flap",
            "Medium Boy Flap"
        ]
    ]
}
PRODUCT_FAMILY_REGEXS[re.compile("(?=.*Flap)", re.IGNORECASE)] = "Double Flap"
for family in ["Mini Boy Flap", "Small Boy Flap", "Medium Boy Flap"]:
    new_family = family.replace("Flap", "Bag")
    pattern = re.compile(
        "".join([f"(?=.*{phrase})" for phrase in new_family.split(" ")]),
        re.IGNORECASE)
    PRODUCT_FAMILY_REGEXS[pattern] = family

LUXE_DU_JOUR_CONDITION_TO_PRODUCT_CONDITION = {
    "10/10 (brand new)": CONDITIONS[0],
    "9.7/10 (like new)": CONDITIONS[1],
    "9.5/10 (some minor flaws)": CONDITIONS[1],
    "9/10 (some visible wear)": CONDITIONS[2],
    "8.5/10 (decent condition)": CONDITIONS[3],
    "8/10 (average condition)": CONDITIONS[4]
}


def lambda_handler(event, context):
    """
    Runs the lambda, scraping Luxe du Jour and saving to an S3 bucket.
    
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

    today = date.today().isoformat()
    search_url = f"{BASE_URL}home/search"
    params = {
        "brands": None,
        "query": None,
        "page": None,
        "conditions": None,
        "categories": "bags",
        "purchaseTypes": "buy",
        "sort": "date",
        "order": "desc",
        "views": "home"
    }
    products = []
    shuffle(BRAND_QUERY_COMBOS)
    for (brand, query) in BRAND_QUERY_COMBOS:
        temp_conditions = sample(
            LUXE_DU_JOUR_CONDITION_TO_PRODUCT_CONDITION.keys(),
            k=len(LUXE_DU_JOUR_CONDITION_TO_PRODUCT_CONDITION.keys()))
        for luxe_du_jour_condition in temp_conditions:
            params["brands"] = brand
            params["query"] = query
            params["conditions"] = luxe_du_jour_condition
            params["page"] = 0
        
            more_to_fetch = True
            while more_to_fetch:
                params["page"] += 1
                response = session.get(search_url, params=params)
                soup = BeautifulSoup(response.text, features="html.parser")
                script_tag = soup.find("script", attrs={"id": "__NEXT_DATA__"})
                script_json = loads(script_tag.text)
                search_data = script_json["props"]["pageProps"]["searchData"]
                items = search_data["items"]
                more_to_fetch = search_data["totalPages"] > params["page"]
            
                for item in items:
                    brand_name = item["brand"]
                    
                    product_name = item["title"]
                    
                    if "salesPrice" in item and item["salesPrice"]:
                        price = float(item["salesPrice"]["max"])
                    else:
                        price = float(item["price"]["max"])
                    
                    condition = (
                        LUXE_DU_JOUR_CONDITION_TO_PRODUCT_CONDITION[
                            luxe_du_jour_condition])
                    
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
                        source="Luxe du Jour",
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