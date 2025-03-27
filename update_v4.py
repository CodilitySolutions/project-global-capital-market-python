import asyncio
from database import Database
from main import analyse_address_using_openai, analyse_location_image, get_average_cost, get_cost, get_neighbourhood_address
import pandas as pd

import os
from dotenv import load_dotenv
import pymssql

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "dot.env"))

server = os.getenv("DB_HOST")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASS")

async def analyse_data():
    db = Database()
    records = db.read_user_data()
    
    conn = pymssql.connect(server, username, password, database, as_dict=True)
    cursor = conn.cursor()
    counter = 0

    for row in records:
        counter += 1
        data = []
        accountid = row["accountid"]
        
        country = row["country"]
        city = row["city"]
        address = row["address"]

        original_address = ""

        if country != None and len(country) > 0:
            original_address += "country="+str(country)
        
        if city != None and len(city) > 0:
            original_address += ", city="+str(city)
        
        if address != None and len(address) > 0:
            original_address += ", address="+str(address)
        
        print("---------------------------------------------------")
        print('counter: ', counter)
        print('accountid: ', accountid)
        print('original_address: ', original_address)

        if address and city:
            neighborhood_address = await get_neighbourhood_address(original_address)
        else:
            data.append((accountid, "", 0, "", "", "", "", 0))
            # db.insert_data(data)
            continue

        if len(neighborhood_address) > 0:
            neighborhood_cost = await get_cost(neighborhood_address, str(city), str(country))
            street_cost = await get_cost(original_address, str(city), str(country))
            print('street_cost: ', street_cost)
            print('neighborhood_cost: ', neighborhood_cost)
            response, is_valid_address = await analyse_location_image(neighborhood_address)
            
            if is_valid_address and len(response) > 0:
                build_cost = response.get(response["build_cost"], 0)
                try:
                    build_cost = float(build_cost)
                except:
                    build_cost = 0
                # image_people_type 
                data.append((accountid, neighborhood_cost, street_cost, build_cost, str(response["people_type"]), "", "", ))
            else:
                # street_people_type, neighbourhood_people_type
                response = await analyse_address_using_openai(neighborhood_address)
                data.append((accountid, neighborhood_cost, street_cost, 0, "", str(response["street_people_type"]), str(response["neighbourhood_people_type"]), ))
            db.update_cost_data(data)
        else:
            average_cost = await get_average_cost(original_address)
            print('Average cost: ', average_cost)
            data.append((accountid, average_cost, 1))
            db.insert_cost(data)


if __name__ == "__main__":
    asyncio.run(analyse_data())