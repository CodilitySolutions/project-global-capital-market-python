import base64
import json
from PIL import Image
from io import BytesIO
import httpx
from app.openai_utils.assistant_client import client
from app.settings.config import GOOGLE_MAP_API_KEY, CHATGPT_MODEL
from app.settings.logger import logger

async def analyse_location_image(address):
    logger.info("🤖 [analyse_location_image] Function started.")
    is_valid = False
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_MAP_API_KEY
    }

    try:
        geocode_request = httpx.AsyncClient()
        geocode_response = await geocode_request.get(geocode_url, params=params)
        geocode_response = geocode_response.json()
    except Exception as e:
        logger.error(f"❌ [analyse_location_image] Failed to get geocode response: {e}")
        return {'object': '', 'area_type': '', 'image_people_type': '', 'property_type': ''}, False

    response = {'object': '', 'area_type': '', 'image_people_type': '', 'property_type': ''}

    if geocode_response["status"] == "OK":
        location = geocode_response["results"][0]["geometry"]["location"]
        lat, lon = location["lat"], location["lng"]
        street_view_url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={lat},{lon}&key={GOOGLE_MAP_API_KEY}"

        try:
            street_view_request = httpx.AsyncClient()
            street_view_response = await street_view_request.get(street_view_url)

            if street_view_response.status_code == 200:
                image = Image.open(BytesIO(street_view_response.content))
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                logger.info("[analyse_location_image] Image fetched successfully, sending to OpenAI...")

                ai_response = await client.chat.completions.create(
                    model=CHATGPT_MODEL,
                    temperature=0,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert in property image analysis and socio-economic categorization."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """
Analyze the provided image and return a response strictly in the JSON format described below:

- Extract the following details from the image clearly and explicitly:
    - **object:** Identify the primary object visible or return "no image detected" if no clear object is present.
    - **area_type:** Classify the area as "Commercial" or "Residential" based on the image.
    - **image_people_type:** Determine the socio-economic class of the residents visible or inferred clearly from the image (e.g., Wealthy, Upper Class, Mid Class, Low Class).
    - **property_type:** Specifically classify the property type shown (e.g., luxurious home, row house, apartment building, commercial office, shop, etc.).

- If any information cannot be determined from the image, do NOT return "unknown" or "not available". Instead, provide a plausible and relevant location (e.g., a city, district, or locality name) from the city or state inferred from the image.

Ensure the JSON response is formatted exactly as follows and do not wrap with markdown or ```json:

{
    "object": "STRING",
    "area_type": "STRING",
    "image_people_type": "STRING",
    "property_type": "STRING"
}
"""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_str}"
                                    }
                                },
                            ],
                        }
                    ],
                )

                response = ai_response.choices[0].message.content

                if type(response) != "json":
                    try:
                        response = json.loads(response.replace("'", "\""))
                        is_valid = True
                        logger.info(f"[analyse_location_image] AI response parsed successfully: {response}")
                    except Exception as e:
                        logger.warning(f"[analyse_location_image] Failed to parse AI response: {e}")

            else:
                logger.error("[analyse_location_image] Failed to fetch location image from Google Street View.")

        except Exception as e:
            logger.error(f"[analyse_location_image] Error while processing Street View image: {e}")
    else:
        logger.warning("[analyse_location_image] Failed to get latitude and longitude from geocoding API.")

    return response, is_valid
