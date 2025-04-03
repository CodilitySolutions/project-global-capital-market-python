import os
import openai
import json
from database import Database
import httpx
from PIL import Image
from io import BytesIO
import re

import requests
from serpapi import GoogleSearch
import os

import base64
import asyncio

from dotenv import load_dotenv

import json
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "dot.env"))


SERP_API_KEY = os.getenv("SERP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")

# client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

import json

def clean_openai_json(raw_response: str) -> str:
    raw_response = raw_response.strip()
    raw_response = raw_response.replace("“", "\"").replace("”", "\"").replace("’", "'")

    try:
        data = json.loads(raw_response)
        # Accept either:
        # - A dict with "properties"
        # - A top-level list of property dictionaries
        if (isinstance(data, dict) and "properties" in data) or isinstance(data, list):
            return json.dumps(data, indent=2)
    except Exception as e:
        print("❌ JSON decode error:", e)

    return "[]"


# async def get_openai_response(prompt):
#     result=""

#     try:
#         response = await client.chat.completions.create(
#             model=CHATGPT_MODEL,
#             messages=[{"role": "user", "content": prompt}]
#         )
#         result = response.choices[0].message.content
#     except Exception as e:
#         print("Exception: ", e)

#     return result

# using openai assistant for chat 
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

async def get_openai_response(prompt):
    result = ""

    try:
        # Step 1: Create a Thread
        thread = await client.beta.threads.create()

        # Step 2: Post the prompt as a message
        await client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        # Step 3: Run the Assistant
        run = await client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Step 4: Wait for completion
        while True:
            run_status = await client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            await asyncio.sleep(1)

        # Step 5: Get the messages (assistant's reply)
        messages = await client.beta.threads.messages.list(thread_id=thread.id)
        result = messages.data[0].content[0].text.value

    except Exception as e:
        print("Exception: ", e)

    return result


async def get_cost(neighborhood_address, city, country):
    cost_prompt = "Address: "+neighborhood_address+", city: "+city+", country: "+country+"\nWhat is per meter square cost in dollar of property in this area?\nInclude fields: 'cost', 'address'. Do not include currency symbol in the response.\nReturn the JSON formatted with {} and don't wrap with ```json."

    response = await get_openai_response(cost_prompt)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            print('response: ', response)
        except:
            response = {"cost": 0}

    cost = response.get("cost", 0)
    try:
        return float(cost)
    except:
        return 0


async def get_average_cost(full_address):
    average_cost_prompt = full_address+"\n\nWhat is the average per meter square cost in dollar of property in this area?\nInclude fields: 'cost', 'address'. Do not include currency symbol in the response.\nReturn the JSON formatted with {} and don't wrap with ```json."

    response = await get_openai_response(average_cost_prompt)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            print('response: ', response)
        except:
            response = {"cost": 0}

    average_cost = response.get("cost", 0)
    try:
        return float(average_cost)
    except:
        return 0


async def get_neighbourhood_address(full_address):
    neighborhood_prompt = full_address+"\n\nIn which neighborhood is this street located?\nProvide response in {'address': neighborhood_address} format only.\nReturn the JSON formatted with {} and don't wrap with ```json.\nNeighborhood should not contains single quote and apostrophe s.\n If neighborhood not found than {'address': '', 'error': error}. Not include unknown or not available in response."

    response = await get_openai_response(neighborhood_prompt)
    print('get_neighbourhood_address response: ', response)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            # print('response: ', response)
        except:
            response = {"address": ""}

    return response.get("address", "")


async def analyse_address_using_openai(address):
    response = {'object': '', 'area_type': '', 'street_people_type': '', 'property_type': '', 'people_type': '', 'neighbourhood_people_type': ''}

    response = await client.chat.completions.create(
        model=CHATGPT_MODEL,
        temperature=0,
    messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Address: "+address+"\nGive me response in this json format: {'area_type': 'commercial or residential', 'street_people_type': 'which type of peoples are living in the street like Wealthy, Upper Class, Mid Class, Low Class', 'property_type': 'type of property in that area like luxurius home, raw house etc', 'people_type': 'which type of people are living in this address like Wealthy, Upper Class, Mid Class, Low Class', 'neighbourhood_people_type': 'which type of people are living in the neighbourhood like Wealthy, Upper Class, Mid Class, Low Class'}\nReturn the JSON formatted with {} and don't wrap with ```json.",
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

    response = {'object': '', 'area_type': '', 'image_people_type': '', 'property_type': ''}

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
            # print('img_str: ', img_str)

            response = await client.chat.completions.create(
                model=CHATGPT_MODEL,
                temperature=0,
    messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this image and give me response in this json format:
                                        {'object': 'detect the object or no image detected', 'area_type': 'which type of property is it like commercial or residential', 'image_people_type': 'which type of peoples are living there like Wealthy, Upper Class, Mid Class, Low Class', 'property_type': 'detect property type like luxurius home, raw house etc'}
                                        \nReturn the JSON formatted with {} and don't wrap with ```json. Should not contain unknown or not available in response if any information not found instead of that return any location in that city or state.
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
    if url.lower().endswith('.pdf'):
        print('No need to scrap those')
        return None

    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()  # Raise error for failed requests (4xx, 5xx)
        html_content = response.text  # Get the HTML content

        # Remove head tag and its content, keep only body tag and its content
        body_content = re.search(r'<body.*?>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_content:
            return body_content.group(1)
        else:
            return html_content  # Return original content if body tag not found
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
        Analyze the html_data that I provided to you and Return the JSON formatted and don't wrap with ```json.. From that provide me the titles that are available in html content, title of the properties , descriptions of the properties that are in the html content , Provide prices (do not convert the price, give me same as in provided html), Convert these prices to dollar and provide these to me where coversion rate is {covert_price_to_dollar} , Provide square meters and if square meters is not provided then use title and description to guess area in square meters, Provide per square meter price in USD also provide me details Url. Ensure that you only include Flat / Apartment, House or Commercial properties and exclude any other property types.
        Provide a minimum of 10 to 20 results in following structured JSON format:
         {{'title': STRING, 
              'description': STRING, 'price': MONEY, 'price_in_USD': MONEY, 
              'square_meter': INTEGER,
              'per_square_meter': MONEY,
              'details_url': STRING}}

        HTML Content (trimmed for token limit):
        {html_data[:100000]}
        """

        response = await client.chat.completions.create(
            model=CHATGPT_MODEL,
            temperature=0,
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


async def get_average_price_people_type(scaped_responses):
    average_prompt = scaped_responses+"\n\nThe text given above has all the openAI responses of scraped data from multiple websites. In given text ignore OpenAI responses that are not in json and just consider OpenAI responses in the above text that are in json {'title': 'listed property title' , 'description': 'listed property title', 'price': 'price of property', 'price_in_USD': 'price of property in USD', 'square_meter': 'size / area of property ', 'details_url': 'details page link of property'} format only.\n Also Calculate and Return average price of square per meter in USD and median price of square per meter in USD but do not put USD OR $ SIGN in {'average': 'average price of square per meter in USD', 'median': 'median price of square per meter in USD', 'street_people_type': 'which type of peoples are living in the street like Wealthy, Upper Class, Mid Class, Low Class', 'property_type': 'type of property in that area like luxurius home, raw house etc', 'people_type': 'which type of people are living in this address like Wealthy, Upper Class, Mid Class, Low Class', 'neighbourhood_people_type': 'which type of people are living in the neighbourhood like Wealthy, Upper Class, Mid Class, Low Class' } in the JSON formatted with {} and don't wrap with ```json.\n If average not found then response should be {'average': '', 'error': error}. Not include unknown or not available in response."

    # response = await get_openai_response(average_prompt)
    response = await client.chat.completions.create(
        model=CHATGPT_MODEL,
        temperature=0,
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

    response_text = parse_response(response.choices[0].message.content)
    print('response_text from parse_response: ', response_text)

    return response_text


def parse_response(response_text):
    try:
        # Detect if response is wrapped in a code block (```json ... ```)
        match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if match:
            response_text = match.group(1)  # Extract only JSON content

        # Ensure proper quotes for JSON parsing
        response_text = response_text.replace("'", "\"")

        # Convert string to JSON
        response_json = json.loads(response_text)

        print('Parsed Data --------get_average_price_people_type---: ', response_json)

        # Extract and convert "average" safely
        average = response_json.get("average", "")
        street_people_type = response_json.get("street_people_type", "")
        property_type = response_json.get("property_type", "")
        neighbourhood_people_type = response_json.get("neighbourhood_people_type", "")
        print('extracted average: ', average)
        print('extracted street_people_type: ', street_people_type)
        print('extracted property_type: ', property_type)
        print('extracted neighbourhood_people_type: ', neighbourhood_people_type)
        # return int(float(average)) if average else ""  # Convert safely
        return response_json

    except json.JSONDecodeError:
        print("Failed to parse OpenAI response as JSON. Raw response:", response_text)
    except ValueError:
        print("Failed to convert average to whole number. Raw average:", average)

    return ""

async def cost_in_dollar(country):
    params = {
        "engine": "google",
        "q": f"1 {country} currency in USD",
        "api_key": SERP_API_KEY,
    }
    search1 = GoogleSearch(params)
    results1 = search1.get_dict()
    organic_results1 = results1.get("organic_results", [])
    # print("organic_results1: ", organic_results1)
    wise_snippets = [result['snippet_highlighted_words'] for result in organic_results1 if result.get('source') == 'Wise']

    print("Snippets from Wise:------------", wise_snippets[0])
    return wise_snippets[0]

async def get_scrap_results(country, city, address, price_in_dollars):

    # Step 1: Fetch Results from SERP API
    print("\n🔍 Fetching results from SERP API...")
    # db = Database()
    # sources = db.read_property_sites_data(country, city, address)

    # if sources:
    #     print("sources", sources)

    params = {
        "engine": "google",
        "q": f"Find houses, flats, apartments, commercial property listings for sale in {country} having City {city}, address {address}",
        "api_key": SERP_API_KEY,
    }

    # print(f"params = {params}")

    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results.get("organic_results", [])

    # Extracting links from organic_results
    links = [result["link"] for result in organic_results]



    # print(f"params = {params}")


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
        accumulated_opneAI_response = ""
        total_records = 0
        min_required_records = 10

        for i, link_url in enumerate(links):
            print(f"🌍 Fetching HTML content from: {link_url}")

            try:
                html_data = await fetch_html(link_url)
                print(f"✅ HTML content fetched successfully from link {i + 1}.")

                # Save the HTML content to a file
                file_path = f"scraped_{i + 1}.html"
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(html_data)

                print(f"📂 HTML content saved to {file_path}")
                opneAI_response = await fetch_openAI_results(file_path, price_in_dollars)

                # Count entries if possible
                try:
                    cleaned_response = clean_openai_json(opneAI_response)
                    print('cleaned_response ++: ', cleaned_response)
                    data = json.loads(cleaned_response)
                    print('cleaned_response data ++: ', data)
                    if isinstance(data, list):
                        total_records += len(data)
                    elif isinstance(data, dict):
                        total_records += 1
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON error: {e}")
                    print(f"Raw OpenAI response (truncated): {opneAI_response[:300]}")
            
                    print(f"⚠️ Could not parse record count from site {i+1}: {e}")

                accumulated_opneAI_response += opneAI_response

                with open(f"openai_{i + 1}.txt", "w", encoding="utf-8") as file:
                    file.write(opneAI_response)
                print(f"📂 Parsed content saved to openai_{i + 1}.txt")

                if total_records >= min_required_records:
                    print(f"✅ Minimum of {min_required_records} records reached. Stopping early.")
                    break

            except Exception as e:
                print(f"❌ Failed to retrieve data from link {i + 1}. Error: {e}")
                # break
            except Exception as e:
                print(f"❌ Failed to retrieve data from link {i + 1}. Error: {e}")
                html_data = ""

        # Step 3: Process opneAI_response with OpenAI API
        print('accumulated_opneAI_response: ', accumulated_opneAI_response)
        average_price_people_type = await get_average_price_people_type(accumulated_opneAI_response)
        print('average_price_people_type returned: ', average_price_people_type)

        # if average_cost not in ['', 0]:
        #     return average_cost

        return average_price_people_type
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


        cost_in_dollars = await cost_in_dollar(country)
        #Now we are going to get the cost of the address
        scrap_results = await get_scrap_results(country, city, address,cost_in_dollars)
        print('scrap_results: ', scrap_results)

        # CASE 1: If Scrap results are found
        if scrap_results and len(scrap_results) and len(scrap_results) > 0:
            try:
                neighborhood_cost = int(float(scrap_results.get("median", 0)))
                street_cost = int(float(scrap_results.get("average", 0)))
            except Exception as e:
                print(f"❌ Failed to extract cost values from scrap_results: {e}")
                neighborhood_cost = 0
                street_cost = 0

            try:
                response, is_valid_address = await analyse_location_image(original_address)
                print('analyse_location_image response: ', response)

                if is_valid_address and response["object"] != 'no image detected' and response["object"] != 'no object detected' and response["object"] != 'no imagery available' and len(response) > 0:
                    # image_people_type
                    
                    analyse_address_response = await analyse_address_using_openai(original_address)
                    data.append((
                        accountid, 
                        neighborhood_cost, 
                        street_cost, 
                        0, 
                        str(response["image_people_type"]), 
                        str(scrap_results.get("street_people_type", analyse_address_response.get("street_people_type", ""))), 
                        str(scrap_results.get("neighbourhood_people_type", analyse_address_response.get("neighbourhood_people_type", ""))), 
                        str(response["object"]), 
                        str(response["area_type"]), 
                        str(response["property_type"]), 
                        1, 
                        address, 
                        str(scrap_results.get("people_type", analyse_address_response.get("people_type", "")))
                    ))
                    print('data+++++ if +++++++: ', data)
                    db.update_cost_data(data)
                else:
                    # street_people_type, neighbourhood_people_type, people_type
                    print('neighborhood_address: not found')
                    analyse_address_response = await analyse_address_using_openai(original_address)
                    data.append((
                        accountid, 
                        neighborhood_cost, 
                        street_cost, 
                        0, 
                        "", 
                        str(scrap_results.get("street_people_type", analyse_address_response.get("street_people_type", ""))), 
                        str(scrap_results.get("neighbourhood_people_type", analyse_address_response.get("neighbourhood_people_type", ""))), 
                        "no imagery available", 
                        str(analyse_address_response["area_type"]), 
                        str(analyse_address_response["property_type"]), 
                        1, 
                        address, 
                        str(scrap_results.get("people_type", analyse_address_response.get("people_type", "")))
                    ))
                    print('data+++++ else +++++++: ', data)
                    db.update_cost_data(data)
            except Exception as e:
                print(f"❌ Database or processing operation failed: {e}")
        else:
            print('❌ scrap_results: empty')

        # CASE 2: If address is NOT found AND neighborhood is found
        # CASE 3: If address is found and neighborhood is NOT found


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
