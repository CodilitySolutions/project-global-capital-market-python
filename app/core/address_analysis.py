import json
from app.openai_utils.assistant_client import client
from app.settings.config import CHATGPT_MODEL
from app.settings.logger import logger
from app.openai_utils.assistant_client import get_openai_response

async def get_cost(neighborhood_address, city, country):
    cost_prompt = (
        f"Address: {neighborhood_address}, city: {city}, country: {country}\n"
        "What is per meter square cost in dollar of property in this area?\n"
        "Include fields: 'cost', 'address'. Do not include currency symbol in the response.\n"
        "Return the JSON formatted with {} and don't wrap with ```json."
    )

    response = await get_openai_response(cost_prompt)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            logger.info(f"[get_cost] Parsed response: {response}")
        except Exception as e:
            logger.warning(f"[get_cost] Failed to parse JSON. Defaulting to cost=0. Error: {e}")
            response = {"cost": 0}

    cost = response.get("cost", 0)
    try:
        return float(cost)
    except:
        logger.warning("[get_cost] Cost could not be converted to float. Returning 0.")
        return 0

async def get_average_cost(full_address):
    average_cost_prompt = (
        f"{full_address}\n\nWhat is the average per meter square cost in dollar of property in this area?\n"
        "Include fields: 'cost', 'address'. Do not include currency symbol in the response.\n"
        "Return the JSON formatted with {} and don't wrap with ```json."
    )

    response = await get_openai_response(average_cost_prompt)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            logger.info(f"[get_average_cost] Parsed response: {response}")
        except Exception as e:
            logger.warning(f"[get_average_cost] Failed to parse JSON. Defaulting to cost=0. Error: {e}")
            response = {"cost": 0}

    average_cost = response.get("cost", 0)
    try:
        return float(average_cost)
    except:
        logger.warning("[get_average_cost] Cost could not be converted to float. Returning 0.")
        return 0

async def get_neighbourhood_address(full_address):
    neighborhood_prompt = (
        f"{full_address}\n\nIn which neighborhood is this street located?\n"
        "Provide response in {'address': neighborhood_address} format only.\n"
        "Return the JSON formatted with {} and don't wrap with ```json.\n"
        "Neighborhood should not contain single quote and apostrophe s.\n"
        "If neighborhood not found then {'address': '', 'error': error}."
    )

    response = await get_openai_response(neighborhood_prompt)
    logger.info(f"[get_neighbourhood_address] Raw response: {response}")
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
        except Exception as e:
            logger.warning(f"[get_neighbourhood_address] Failed to parse JSON: {e}")
            response = {"address": ""}

    return response.get("address", "")

async def analyse_address_using_openai(address):
    response = await client.chat.completions.create(
        model=CHATGPT_MODEL,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Address: {address}\n\n"
                        "Analyze the given address and respond strictly with a JSON object matching this exact structure:\n"
                        "{\n"
                        '  "area_type": STRING,                  // Either "commercial" or "residential"\n'
                        '  "street_people_type": STRING,         // Only "Wealthy", "Upper Class", "Mid Class", or "Low Class"\n'
                        '  "property_type": STRING,              // Specifically classify the property type shown (e.g., luxurious home, row house, apartment building, commercial office, shop, etc.).\n'
                        '  "people_type": STRING,                // Only "Wealthy", "Upper Class", "Mid Class", or "Low Class"\n'
                        '  "neighbourhood_people_type": STRING   // Only "Wealthy", "Upper Class", "Mid Class", or "Low Class"\n'
                        "}\n\n"
                        "Rules for JSON response:\n"
                        "1. Do NOT wrap your response in markdown or triple backticks.\n"
                        "2. Each field must have exactly the specified values only.\n"
                        "3. If unable to determine any field, Default to \"residential\" for area_type and Default to \"home\" for property_type.\n"
                        "4. **Do not** wrap the final output in markdown syntax like triple backticks or `json`.\n"
                        "5. The following fields can **only** have one of these four exact string values:\n"
                        '   - "Wealthy"\n'
                        '   - "Upper Class"\n'
                        '   - "Mid Class"\n'
                        '   - "Low Class"\n'
                        "6. Applicable fields:\n"
                        '   - street_people_type\n'
                        '   - people_type\n'
                        '   - neighbourhood_people_type\n'
                        ),
                    }
                ],
            }
        ],
    )
    response = response.choices[0].message.content

    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            logger.info(f"[analyse_address_using_openai] Parsed response: {response}")
        except Exception as e:
            logger.warning(f"[analyse_address_using_openai] Failed to parse JSON: {e}")

    return response
