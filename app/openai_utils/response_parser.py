import json
import re
from app.settings.logger import logger

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

        logger.info("[parse_response] Parsed JSON successfully.")
        logger.debug(f"[parse_response] Full parsed data: {response_json}")

        # Extract and log key fields
        average = response_json.get("average", "")
        street_people_type = response_json.get("street_people_type", "")
        property_type = response_json.get("property_type", "")
        neighbourhood_people_type = response_json.get("neighbourhood_people_type", "")

        logger.info(f"[parse_response] Extracted average: {average}")
        logger.info(f"[parse_response] Extracted street_people_type: {street_people_type}")
        logger.info(f"[parse_response] Extracted property_type: {property_type}")
        logger.info(f"[parse_response] Extracted neighbourhood_people_type: {neighbourhood_people_type}")

        return response_json

    except json.JSONDecodeError:
        logger.warning(f"[parse_response] Failed to parse OpenAI response as JSON. Raw response: {response_text}")
    except ValueError as e:
        logger.warning(f"[parse_response] Failed to convert average. Error: {e}")

    return ""
