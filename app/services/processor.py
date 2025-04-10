import json
from urllib.parse import urlparse
from serpapi import GoogleSearch
import asyncio

from app.scrapers.privateproperty_scraper import PrivatePropertyScraper
from app.scrapers.property24_scraper import Property24Scraper
from app.scrapers.utils import clean_openai_json
from app.core.html_processing import fetch_html, fetch_openAI_results
from app.core.cost_analysis import get_average_price_people_type
from app.core.image_analysis import analyse_location_image
from app.core.address_analysis import get_cost, get_average_cost, get_neighbourhood_address, analyse_address_using_openai
from app.settings.config import SERP_API_KEY
from app.settings.logger import logger
from database import Database
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "log"
LOG_DIR.mkdir(exist_ok=True)

SCRAPER_REGISTRY = {
    'property24.com': Property24Scraper(),
    'privateproperty.co.za': PrivatePropertyScraper(),
}

# cache dictionary for currency conversion
conversion_cache = {}

def extract_domain(link):
    try:
        domain = urlparse(link).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

async def cost_in_dollar(country):
    if country in conversion_cache:
        logger.info(f"📦 [cost_in_dollar] Using cached rate for {country}")
        return conversion_cache[country]

    logger.info(f"📊 [cost_in_dollar] Fetching conversion rate for {country}...")
    params = {
        "engine": "google",
        "q": f"1 {country} currency in USD",
        "api_key": SERP_API_KEY,
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results.get("organic_results", [])
    wise_snippets = [result['snippet_highlighted_words'] for result in organic_results if result.get('source') == 'Wise']

    if wise_snippets:
        rate = wise_snippets[0]
        conversion_cache[country] = rate
        logger.info(f"✅ [cost_in_dollar] Fetched and cached rate: {rate}")
        return rate

    logger.warning(f"⚠️ [cost_in_dollar] No conversion rate found for {country}. Using fallback.")
    conversion_cache[country] = ["", "0 USD"]
    return ["", "0 USD"]

async def get_scrap_results(country, city, address, price_in_dollars):
    logger.info("📊 [get_scrap_results] Started...")

    params = {
        "engine": "google",
        "q": f"Find houses, flats, apartments, commercial property listings for sale in {country} having City {city}, address {address}",
        "api_key": SERP_API_KEY,
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results.get("organic_results", [])
    links = [result["link"] for result in organic_results]

    if not links:
        logger.warning("❌ [get_scrap_results] No SERP links found.")
        return 0

    logger.info(f"✅ [get_scrap_results] Found {len(links)} SERP links.")

    domain_priority = {
        'privateproperty.co.za': 1,
        'property24.com': 2,
    }

    sorted_links = sorted(
        links,
        key=lambda link: domain_priority.get(extract_domain(link), float('inf'))
    )

    total_records = 0
    min_required_records = 8
    accumulated_opneAI_response = ""

    for i, link_url in enumerate(sorted_links):
        logger.info(f"🌍 [get_scrap_results] Fetching from: {link_url}")

        try:
            domain = extract_domain(link_url)
            scraper = SCRAPER_REGISTRY.get(domain)
            if scraper:
                logger.info(f"🔍 Using dynamic scraper for {domain}")
                properties = scraper.scrape(link_url, price_in_dollars, i)
                opneAI_response = json.dumps(properties)
            else:
                html_data = await fetch_html(link_url)
                logger.info(f"✅ HTML content fetched from link {i + 1}")

                file_path = LOG_DIR / f"scraped_{i + 1}.html"
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(html_data)

                logger.info(f"📂 HTML saved to {file_path}")
                opneAI_response = await fetch_openAI_results(file_path, price_in_dollars)

            try:
                cleaned_response = clean_openai_json(opneAI_response)
                data = json.loads(cleaned_response)
                if isinstance(data, list):
                    total_records += len(data)
                elif isinstance(data, dict):
                    for value in data.values():
                        if isinstance(value, list):
                            total_records += len(value)
                            break
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON parsing error: {e}")

            accumulated_opneAI_response += opneAI_response

            with open(LOG_DIR / f"openai_{i + 1}.txt", "w", encoding="utf-8") as file:
                file.write(opneAI_response)

            if total_records >= min_required_records:
                logger.info("✅ Minimum data threshold met. Breaking early.")
                break

        except Exception as e:
            logger.error(f"❌ Failed to retrieve data from link {i + 1}: {e}")

    logger.info(f"📊 Total Records Collected: {total_records}")
    logger.debug(f"accumulated_opneAI_response: {accumulated_opneAI_response[:300]}...")
    return await get_average_price_people_type(accumulated_opneAI_response)

async def calculate_cost():
    logger.info("🚀 [calculate_cost] Cost estimation started...")
    db = Database()
    records = db.read_user_data()

    for row in records:
        logger.info("---------------------------------------------------")
        data = []
        accountid = row["accountid"]
        city = ''
        original_address = ""

        if row.get("country"):
            country = str(row["country"])
            original_address += "country=" + country

        if row.get("city"):
            city = str(row["city"])
            original_address += ", city=" + city

        if row.get("address"):
            address = str(row["address"])
            original_address += ", address=" + address

        logger.info(f"📍 Processing address: {original_address}")

        cost_in_dollars = await cost_in_dollar(country)
        scrap_results = await get_scrap_results(country, city, address, cost_in_dollars)
        logger.debug(f"🧾 scrap_results: {scrap_results}")

        if scrap_results and len(scrap_results) > 0:
            try:
                neighborhood_cost = int(float(scrap_results.get("median", 0)))
                street_cost = int(float(scrap_results.get("average", 0)))
            except Exception as e:
                logger.error(f"❌ Failed to extract cost values: {e}")
                neighborhood_cost = 0
                street_cost = 0

            try:
                response, is_valid_address = await analyse_location_image(original_address)
                logger.debug(f"🖼️ analyse_location_image: {response}")

                if is_valid_address and response["object"] not in ['no image detected', 'no object detected', 'no imagery available']:
                    analyse_address_response = await analyse_address_using_openai(original_address)
                    data.append((
                        accountid, neighborhood_cost, street_cost, 0,
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
                    logger.info("✅ Image + address analysis complete with valid image.")
                else:
                    analyse_address_response = await analyse_address_using_openai(original_address)
                    data.append((
                        accountid, neighborhood_cost, street_cost, 0,
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
                    logger.info("ℹ️ Used address analysis fallback (no image available).")

                logger.warning(f"📊 [calculate_cost] Data: {data}")
                db.update_cost_data(data)

            except Exception as e:
                logger.exception(f"❌ Failed during address/image analysis or DB update: {e}")
        else:
            data.append((
                        accountid, 0, 0, 0,
                        "",
                        "",
                        "",
                        "address not found",
                        "",
                        "",
                        0,
                        address,
                        ""
                    ))
            logger.warning(f"📊 [calculate_cost] Data: {data}")
            db.update_cost_data(data)
            logger.warning("❌ No valid scrap_results returned. updating DB with address not found.")

        await asyncio.sleep(5)

    db.read_cost_data()
