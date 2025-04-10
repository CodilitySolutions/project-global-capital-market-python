import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../../dot.env"))

SERP_API_KEY = os.getenv("SERP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
