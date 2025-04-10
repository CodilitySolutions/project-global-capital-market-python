import json
from app.settings.logger import logger
import requests
from app.settings.config import SCRAPER_API

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
        logger.error(f"❌ [clean_openai_json] JSON decode error: {e}")

    return "[]"

def fallback_scraper(url):
    print("🔄 Using fallback scraper...")
    payload = {
        'api_key': SCRAPER_API,  # Use your actual API key
        'url': url
    }
    try:
        response = requests.get('https://api.scraperapi.com/', params=payload, timeout=30)
        response.raise_for_status()
        print("✅ Fallback scraper succeeded.")
        return response
    except Exception as e:
        print(f"❌ Fallback scraper failed: {e}")
        return None