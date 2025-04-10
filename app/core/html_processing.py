import re
import requests
from app.openai_utils.assistant_client import client
from app.settings.config import CHATGPT_MODEL

async def fetch_html(url):
    print("\n🤖 function fetch_html started ...")
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
    print("\n🤖 function fetch_openAI_results started ...")
    print('covert_price_to_dollar: ', covert_price_to_dollar)
    # Read the saved file content
    with open(filename, "r", encoding="utf-8") as file:
        html_data = file.read()
    if html_data:
        print("\n🤖 Processing HTML content with OpenAI API...")

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
