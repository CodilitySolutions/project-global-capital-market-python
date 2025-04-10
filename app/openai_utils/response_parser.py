import json
import re

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
