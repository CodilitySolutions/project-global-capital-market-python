from app.openai_utils.assistant_client import client
from app.settings.config import CHATGPT_MODEL
from app.openai_utils.response_parser import parse_response
from app.settings.logger import logger

async def get_average_price_people_type(scaped_responses):
    logger.info("📊 [get_average_price_people_type] Function started.")

    average_prompt = scaped_responses + """\n\nThe input text contains multiple OpenAI responses generated from scraped data across various property listing websites.

1. From the input text, **only extract the responses that are in valid JSON format** matching this structure:
{
  "title": "listed property title",
  "description": "description of the listed property",
  "price": "price of property",
  "price_in_USD": "price of property in USD",
  "square_meter": "size / area of property",
  "details_url": "details page link of property"
}

2. Ignore all non-JSON or malformed responses.

3. Based on the valid extracted JSON responses, calculate the **average** and **median price per square meter in USD**. Round the results to the nearest whole number.

4. Then, generate and return a single, final JSON object in the following structure:
{
  "average": INTEGER, // average price per square meter in USD
  "median": INTEGER,  // median price per square meter in USD
  "street_people_type": STRING,        // e.g., "Wealthy", "Upper Class", etc.
  "property_type": STRING,             // e.g., "Wealthy", "Upper Class", etc.
  "people_type": STRING,               // e.g., "Wealthy", "Upper Class", etc.
  "neighbourhood_people_type": STRING  // e.g., "Wealthy", "Upper Class", etc.
}

5. **Do not** include currency symbols like `$` or `USD` in numeric values.

6. **Do not** wrap the final output in markdown syntax like triple backticks or `json`.

7. If average or median cannot be calculated (e.g., missing or invalid data), simply place a **0** rather than using placeholder values like "unknown" or "N/A".

8. The following fields can **only** have one of these four exact string values:
- "Wealthy"
- "Upper Class"
- "Mid Class"
- "Low Class"

Applicable fields:
- street_people_type
- property_type
- people_type
- neighbourhood_people_type
"""

    try:
        response = await client.chat.completions.create(
            model=CHATGPT_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": average_prompt}],
                }
            ],
        )

        response_text = parse_response(response.choices[0].message.content)
        logger.info(f"[get_average_price_people_type] Parsed OpenAI response: {response_text}")
        return response_text

    except Exception as e:
        logger.exception(f"❌ [get_average_price_people_type] Error communicating with OpenAI: {e}")
        return {}
