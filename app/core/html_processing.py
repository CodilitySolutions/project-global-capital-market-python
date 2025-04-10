import re
import requests
from app.openai_utils.assistant_client import client
from app.settings.config import CHATGPT_MODEL
from app.settings.logger import logger

async def fetch_html(url):
    logger.info("🤖 [fetch_html] Function started...")

    if url.lower().endswith('.pdf'):
        logger.info("🛑 [fetch_html] PDF file detected, skipping scraping.")
        return None

    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        html_content = response.text

        body_content = re.search(r'<body.*?>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_content:
            logger.info("✅ [fetch_html] Body content extracted successfully.")
            return body_content.group(1)
        else:
            logger.warning("⚠️ [fetch_html] <body> tag not found, returning full HTML content.")
            return html_content

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ [fetch_html] Error fetching HTML from {url}: {e}")
        return None

async def fetch_openAI_results(filename, covert_price_to_dollar):
    logger.info("🤖 [fetch_openAI_results] Function started.")
    logger.info(f"💰 USD conversion rate used: {covert_price_to_dollar}")

    try:
        with open(filename, "r", encoding="utf-8") as file:
            html_data = file.read()
    except Exception as e:
        logger.error(f"❌ [fetch_openAI_results] Failed to read file {filename}: {e}")
        return ""

    if html_data:
        logger.info("📤 [fetch_openAI_results] Sending HTML content to OpenAI API...")

        prompt = f"""
Analyze the provided HTML content and extract property listings with the following requirements:

- **Property Types:** Only include properties classified explicitly as Flat, Apartment, House, or Commercial. Exclude all other property types.
- **Extract the following data points for each property:**
    - **Title:** Clearly identified property title.
    - **Description:** Full description text.
    - **Price:** Exact price as displayed in HTML content (do NOT convert).
    - **Price in USD:** Convert the extracted price to USD using the conversion rate provided: {covert_price_to_dollar}.
    - **Square Meters (Area):** Extract explicitly provided area in square meters. If area is missing, estimate reasonably using property title and description.
    - **Price per Square Meter in USD:** Calculate by dividing "Price in USD" by "Square Meters".
    - **Details URL:** Full URL link to the property's details page.

- **Output Format:** Return a JSON-formatted list of property entries without wrapping it in markdown or ```json.

- **Number of Results:** Provide between 10 and 20 properties. If fewer than 10 properties are found, return as many as available.

Use the following exact JSON structure for each property:

{{
    "title": "STRING",
    "description": "STRING",
    "price": "MONEY",
    "price_in_USD": "MONEY",
    "square_meter": INTEGER,
    "per_square_meter_in_USD": "MONEY",
    "details_url": "STRING"
}}

HTML Content (trimmed to fit token limit):
{html_data[:100000]}
"""

        try:
            response = await client.chat.completions.create(
                model=CHATGPT_MODEL,
                temperature=0,
                messages=[
                    {"role": "system", "content": "You are an expert in property analysis and pricing."},
                    {"role": "user", "content": prompt}
                ]
            )

            json_response = response.choices[0].message.content
            logger.info("✅ [fetch_openAI_results] Received response from OpenAI.")
            return json_response

        except Exception as e:
            logger.exception(f"❌ [fetch_openAI_results] OpenAI API call failed: {e}")
            return ""
    else:
        logger.warning("❌ [fetch_openAI_results] No HTML content to process.")
        return
