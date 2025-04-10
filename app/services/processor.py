import json
from urllib.parse import urlparse
from serpapi import GoogleSearch
import asyncio

from app.scrapers.privateproperty_scraper import fetch_properties_privateproperty
from app.scrapers.property24_scraper import fetch_properties_property24
from app.scrapers.utils import clean_openai_json
from app.core.html_processing import fetch_html, fetch_openAI_results
from app.core.cost_analysis import get_average_price_people_type
from app.core.image_analysis import analyse_location_image
from app.core.address_analysis import get_cost, get_average_cost, get_neighbourhood_address, analyse_address_using_openai
from app.settings.config import SERP_API_KEY
from database import Database

async def cost_in_dollar(country):
    print("\n📊 function cost_in_dollar started ...")
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
    print("\n📊 function get_scrap_results started ...")

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
        # Create a dictionary with priorities for specific domains
        from urllib.parse import urlparse

        domain_priority = {
            'property24.com': 1,
            'privateproperty.co.za': 2,
            'realtor.com': 3,
            'zillow.com': 4,
            'trulia.com': 5
        }

        def extract_domain(link):
            try:
                domain = urlparse(link).netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                return domain
            except Exception:
                return ""

        for i, link in enumerate(links):
            print(f"original link {i + 1}. {link}")

        sorted_links = sorted(
            links,
            key=lambda link: domain_priority.get(extract_domain(link), float('inf'))
        )

        for i, link in enumerate(sorted_links):
            print(f"sorted link {i + 1}. {link}")



        # Step 2: Fetch HTML Content from each link
        html_data = ""

        opneAI_response = ""
        accumulated_opneAI_response = ""
        total_records = 0
        min_required_records = 8

        for i, link_url in enumerate(sorted_links):
            print(f"🌍 Fetching HTML content from: {link_url}")

            try:
                if "property24.com" in link_url:
                    print(f"🔍 Using Property24 scraper for link {i + 1}.")
                    properties = fetch_properties_property24(link_url, price_in_dollars, i)
                    opneAI_response = json.dumps(properties)
                elif "privateproperty.co.za" in link_url:
                    print(f"🔍 Using privateproperty.co.za scraper for link {i + 1}.")
                    properties = fetch_properties_privateproperty(link_url, price_in_dollars, i)
                    opneAI_response = json.dumps(properties)
                else:
                    html_data = await fetch_html(link_url)
                    print(f"✅ HTML content fetched successfully from link {i + 1}.")

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
                        for value in data.values():
                            if isinstance(value, list):
                                total_records += len(value)
                                break
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
        city = ''
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
