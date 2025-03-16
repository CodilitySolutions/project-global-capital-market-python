import os
import openai
from openai import OpenAI
import json
from database import Database
import httpx
from PIL import Image
from io import BytesIO

import base64
import asyncio

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "dot.env"))


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")

client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

async def get_openai_response(prompt):
    result=""

    try:
        response = await client.chat.completions.create(
            model=CHATGPT_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content
    except Exception as e:
        print("Exception: ", e)

    return result


# async def get_cost(neighborhood_address, city, country):
#     cost_prompt = "Address: "+neighborhood_address+", city: "+city+", country: "+country+"\nWhat is per meter square cost in dollar of property in this area?\nInclude fields: 'cost', 'address'. Do not include currency symbol in the response.\nReturn the JSON formatted with {} and don't wrap with ```json."

#     response = await get_openai_response(cost_prompt)
#     if type(response) != "json":
#         try:
#             response = json.loads(response.replace("'", "\""))
#             print('response: ', response)
#         except:
#             response = {"cost": 0}

#     cost = response.get("cost", 0)
#     try:
#         return float(cost)
#     except:
#         return 0


# async def get_average_cost(full_address):
#     average_cost_prompt = full_address+"\n\nWhat is the average per meter square cost in dollar of property in this area?\nInclude fields: 'cost', 'address'. Do not include currency symbol in the response.\nReturn the JSON formatted with {} and don't wrap with ```json."

#     response = await get_openai_response(average_cost_prompt)
#     if type(response) != "json":
#         try:
#             response = json.loads(response.replace("'", "\""))
#             print('response: ', response)
#         except:
#             response = {"cost": 0}

#     average_cost = response.get("cost", 0)
#     try:
#         return float(average_cost)
#     except:
#         return 0


async def get_neighbourhood_address(full_address):
    neighborhood_prompt = full_address+"\n\nIn which neighborhood is this street located?\nProvide response in {'address': neighborhood_address} format only.\nReturn the JSON formatted with {} and don't wrap with ```json.\nNeighborhood should not contains single quote and apostrophe s.\n If neighborhood not found than {'address': '', 'error': error}. Not include unknown or not available in response."

    response = await get_openai_response(neighborhood_prompt)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            # print('response: ', response)
        except:
            response = {"address": ""}

    return response.get("address", "")


async def analyse_address_using_openai(address):
    response = {'object': '', 'area_type': '', 'people': '', 'property_type': ''}

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Address: "+address+"\nGive me response in this json format: {'area_type': 'which type of properties are in that area like commercial or residential', 'people': 'which type of peoples are living there like High class, wealthy, mid class, low class, or poor', 'property_type': 'type of property in that area like luxurius home, raw house etc'}\nReturn the JSON formatted with {} and don't wrap with ```json.",
                    }
                ],
            }
        ],
    )
    response = response.choices[0].message.content

    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            print('address analyse: ', response)
        except:
            pass
    
    return response


async def analyse_location_image(address):
    is_valid = False
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_MAP_API_KEY
    }
    
    geocode_request = httpx.AsyncClient()
    geocode_response = await geocode_request.get(geocode_url, params=params)
    geocode_response = geocode_response.json()

    response = {'object': '', 'area_type': '', 'people': '', 'property_type': ''}

    if geocode_response["status"] == "OK":

        location = geocode_response["results"][0]["geometry"]["location"]
        lat, lon = location["lat"], location["lng"]

        street_view_url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={lat},{lon}&key={GOOGLE_MAP_API_KEY}"

        street_view_request = httpx.AsyncClient()
        street_view_response = await street_view_request.get(street_view_url)

        if street_view_response.status_code == 200:
            image = Image.open(BytesIO(street_view_response.content))
            #image.save("street_view.png")
            buffered = BytesIO()
            image.save(buffered, format="PNG")

            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this image and give me response in this json format: 
                                        {'object': 'detect the object', 'area_type': 'which type of property is it like commercial or residential', 'people': 'which type 
                                        of peoples are living there like wealthy, or poor', 'property_type': 'detect property type like luxurius home, raw house etc'}
                                        \nReturn the JSON formatted with {} and don't wrap with ```json. Should not contain unknow or not available in response if any information not found instead of that return any location in that city or state.
                                        """,
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                            },
                        ],
                    }
                ],
            )

            response = response.choices[0].message.content

            if type(response) != "json":
                try:
                    response = json.loads(response.replace("'", "\""))
                    is_valid = True
                    print('Data: ', response)
                except:
                    print("Failed to get address analyse response")
            
        else:
            print("Failed to get location image")
    else:
        print("Failed to get latitude and longitude")

    return response, is_valid


async def get_heuristic_cost(country, city, address):
    # sources_prompt = f"Search Flat / Apartment, House or Commercial properties in {country} having City {city} and address {address}. \nFind mean per square meter price for sale. Use sources {sources}. \nIf size of the house or flat is not available, then use 120 square meters for a 3-bedroom house/flat, 185 square meters for a 4-bedroom house/flat, and so on as an assumption. Price should be in USD by taking conversion rate from xe.com. \nReturn the JSON formatted with {{}} and don't wrap with ```json."
    sources_prompt = f"""
Based on historical market trends and general real estate knowledge, 
estimate the average per square meter price for properties in {city}, {country}, specifically at {address}. 
Do not use real-time data, external sources, or current listings. 

Categorize the given location into one of these groups based on general trends 
and provide an estimated price per square meter.

Assume a fixed exchange rate of 1 USD = 800 NGN (or any latest available conversion rate from xe.com). 
If needed, convert local prices into USD using this rate.

Price should be in USD by taking the given conversion rate into account.

Return the JSON formatted with {{"price": estimated_value, "address": "{address}"}} and don't wrap with ```json.
"""

    client = OpenAI(api_key=OPENAI_API_KEY)
    # client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    response = await client.responses.create(
        model="gpt-4-turbo",
        tools=[{ "type": "web_search_preview" }],
        input=sources_prompt
    )

    print("sources response", response)

    # if type(response) != "json":
    #     try:
    #         response = json.loads(response.choices[0].message.content)
    #     except:
    #         response = {"price": 0}

    # price = response.get("price", 0)
    # try:
    #     return float(price)
    # except:
    return 0


async def calculate_cost():
    db = Database()
    records = db.read_user_data()

    for row in records:
        print("---------------------------------------------------")

        data = []
        accountid = row["accountid"]
        # country = row["country"]
        # city = row["city"]
        # address = row["address"]
        original_address = ""

        if row["country"] != None and len(row["country"]) > 0:
            country = str(row["country"])
            original_address += "country=" + country

        if row["city"] != None and len(row["city"]) > 0:
            city = str(row["city"])
            original_address += ", city=" + city

        if row["address"] != None and len(row["address"]) > 0:
            address = str(row["address"])
            original_address += ", address="+ address

        print('original_address:     ', original_address)

        neighborhood_address = await get_neighbourhood_address(original_address)
        print('neighborhood_address: ', neighborhood_address)

        if len(neighborhood_address) > 0:
            cost = await get_heuristic_cost(country, city, address)
            print('cost: ', cost)

            response, is_valid_address = await analyse_location_image(neighborhood_address)

            if is_valid_address and len(response) > 0:
                data.append((
                    accountid, 
                    neighborhood_address, 
                    cost, 
                    str(response["object"]), 
                    str(response["area_type"]), 
                    str(response["people"]), 
                    str(response["property_type"]
                        ), 1))
            else:
                response = await analyse_address_using_openai(neighborhood_address)
                data.append((
                    accountid, 
                    neighborhood_address, 
                    cost, 
                    "", 
                    str(response["area_type"]), 
                    str(response["people"]), 
                    str(response["property_type"]
                        ), 1))

            db.insert_data(data)
        else:
            cost = await get_heuristic_cost(country, city, address)
            print('Average cost: ', cost)

            data.append((accountid, cost, 1))
            db.insert_cost(data)


    db.read_cost_data()


if __name__ == "__main__":
    asyncio.run(calculate_cost())

