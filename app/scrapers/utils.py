import json

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
        print("❌ JSON decode error:", e)

    return "[]"

