import os
import openai
import json
from database import Database
import httpx
from PIL import Image
from io import BytesIO
import requests
from serpapi import GoogleSearch
import os

import base64
import asyncio

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "dot.env"))


SERP_API_KEY = os.getenv("SERP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")

# client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

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


async def fetch_html(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()  # Raise error for failed requests (4xx, 5xx)
        return response.text  # Return the HTML content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HTML from {url}: {e}")
        return None  # Return None if request fails


async def fetch_openAI_results(filename, covert_price_to_dollar):
    # Read the saved file content
    with open(filename, "r", encoding="utf-8") as file:
        html_data = file.read()
    if html_data:
        print("\n🤖 Processing HTML content with OpenAI API...")
        
        prompt = f"""
        Analyze the html_data that I provided to you. From that provide me the titles that are available in html content, title of the properties , descriptions of the properties that are in the html content , Provide prices (do not convert the price, give me same as in provided html), Convert these prices to dollar and provide these to me where coversion rate is {covert_price_to_dollar} , Provide square meters and if square meters is not provided then use description to guess area in square meters using hueristics, Provide per square meter price in USD also provide me details Url. Ensure that you only include Flat / Apartment, House or Commercial properties and exclude any other property types.
        Provide a minimum of 10 to 20 results in structured JSON format with these keys:  
        "title", "description", "price", "price_in_USD", "square_meter", "per_square_meter" ,"details_url".  

        HTML Content (trimmed for token limit):
        {html_data[:100000]}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in property analysis and pricing."},
                {"role": "user", "content": prompt}
            ]
        )
        
        json_response = response.choices[0].message.content
        #   sprint("\n📊 OpenAI Response:\n", json_response)
    else:
        print("❌ No HTML content to process.")   
    return json_response

async def get_average_price_square_per_meter(scaped_responses):
    average_prompt = scaped_responses+"\n\nThe text given above has all the openAI responses of scraped data from multiple websites. In given text ignore OpenAI responses that are not in json and just consider OpenAI in the above text that are in json and return it encapsulated in data {} object of whole json  {'title': 'listed property title' , 'description': 'listed property title', 'price': 'price of property', 'price_in_USD': 'price of property in USD', 'square_meter': 'size / area of property ', 'details_url': 'details page link of property',  } format only.\n Also Calculate and Return average price of square per meter in {'average': 'average price of square per meter'} in the JSON formatted with {} and don't wrap with ```json.\n If average not found then response should be {'average': '', 'error': error}. Not include unknown or not available in response."

    # response = await get_openai_response(average_prompt)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": average_prompt,
                    }
                ],
            }
        ],
    )

    response_text = response.choices[0].message.content

    try:
        response_json = json.loads(response_text.replace("'", "\""))  # Convert string to JSON
        print('Parsed Data --------get_average_price_square_per_meter---: ', response_json)
        average = response_json.get("average", "")
        return int(float(average)) if average else ""  # Ensure whole number value is returned
    except json.JSONDecodeError:
        print("Failed to parse OpenAI response as JSON. Raw response:", response_text)
    except ValueError:
        print("Failed to convert average to whole number. Raw average:", average)
    return ""

async def get_heuristic_cost(country, city, address):

    # Step 1: Fetch Results from SERP API
    print("\n🔍 Fetching results from SERP API...")
    db = Database()
    sources = db.read_property_sites_data(country, city, address)
    
    if sources:
        print("sources", sources)

    params = {
        "engine": "google",
        "q": f"Find property for sale in {country} having City {city}, address {address}",
        "api_key": SERP_API_KEY,
    }

    # print(f"params = {params}")

    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results.get("organic_results", [])

    # Extracting links from organic_results
    links = [result["link"] for result in organic_results]

    params = {
        "engine": "google",
        "q": f"1 {country} currency in USD",
        "api_key": SERP_API_KEY,
    }

    # print(f"params = {params}")

    search1 = GoogleSearch(params)
    results1 = search1.get_dict()
    organic_results1 = results1.get("organic_results", [])
    # print("organic_results1: ", organic_results1)
    wise_snippets = [result['snippet_highlighted_words'] for result in organic_results1 if result.get('source') == 'Wise']

    print("Snippets from Wise:------------", wise_snippets[0])
    # return 0

    # Extracting links from organic_results
    # links = [result["link"] for result in organic_results]

    if links:
        print("✅ SERP API Results:")
        for i, link in enumerate(links):
            print(f"{i + 1}. {link}")

        # Step 2: Fetch HTML Content from each link
        html_data = ""

        opneAI_response = ""


        for i, link_url in enumerate(links):
            print(f"\n🌍 Fetching HTML content from: {link_url}")
            
            try:
                html_data = await fetch_html(link_url)
                print(f"✅ HTML content fetched successfully from link {i + 1}.")
                
                # Save the HTML content to a file
                with open(f"scraped_{i + 1}.html", "w", encoding="utf-8") as file:
                    file.write(html_data)
                print(f"📂 HTML content saved to scraped_{i + 1}.html")
                opneAI_response += await fetch_openAI_results(f"scraped_{i + 1}.html", wise_snippets[0])
                with open(f"openai_{i + 1}.txt", "w", encoding="utf-8") as file:
                    file.write(opneAI_response)
                print(f"📂 parsed content saved to openai_{i + 1}.txt")
                # break
            except Exception as e:
                print(f"❌ Failed to retrieve data from link {i + 1}. Error: {e}")
                html_data = ""
        
        # Step 3: Process opneAI_response with OpenAI API
        print('opneAI_response: ', opneAI_response)
        average_cost = await get_average_price_square_per_meter(opneAI_response)
        print('average_cost returned: ', average_cost)

        if average_cost not in ['', 0]:
            return average_cost

        return 0
    else:
        print("❌ No links found.")
        html_data = ""

    # Step 3: Process HTML with OpenAI API
 
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

        await asyncio.sleep(5)  # Sleep for 1 second after each iteration


    db.read_cost_data()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(calculate_cost())
    finally:
        loop.run_until_complete(asyncio.sleep(1))  # Give time for cleanup
        loop.run_until_complete(loop.shutdown_asyncgens())  # Force shutdown of pending async generators
        loop.close()


