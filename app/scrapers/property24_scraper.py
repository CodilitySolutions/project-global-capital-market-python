from bs4 import BeautifulSoup
import requests
from app.scrapers.base import BaseScraper
from app.settings.logger import logger
from pathlib import Path
from app.scrapers.utils import fallback_scraper

LOG_DIR = Path(__file__).resolve().parent.parent / "log"
LOG_DIR.mkdir(exist_ok=True)


class Property24Scraper(BaseScraper):
    def scrape(self, url: str, usd_rate: list, i: int) -> list:
        logger.info("🤖 [Property24Scraper] Scraper started...")
        logger.info("🌍 Fetching page...")

        try:
            usd_rate_value = float(usd_rate[0].split(',')[1].strip().split(' ')[0])
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
           # response = requests.get(url, headers=headers, timeout=30)
            response = self.safe_request(url, headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            cards = soup.select('a.p24_content')
            if response is None  or not cards or len(cards) == 0:
                logger.info(f"❌ [Property24Scraper] Failed to fetch HTML from request")
                response = fallback_scraper(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.select('a.p24_content')
                if response is None or not cards or len(cards) == 0:
                    logger.info(f"❌ [Property24Scraper] Failed to fetch HTML from scraper api")
                    return []  # Indicates error to caller

        except Exception as e:
            logger.error(f"❌ [Property24Scraper] Failed to fetch HTML: {e}")
            try:
                response = fallback_scraper(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.select('a.p24_content')
                if response is None or not cards or len(cards) == 0:
                    logger.info(f"❌ [PrivatePropertyScraper] Failed to fetch HTML from scraper api")
                    return []  # Indicates error to caller
            except Exception as e:
                return []


        try:
            file_path = LOG_DIR / f"scraped_{i + 1}.html"
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(response.text)
            logger.info(f"📂 [Property24Scraper] HTML content saved to {file_path}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"❌ [Property24Scraper] Failed to write HTML: {e}")

        logger.info("✅ Page loaded. Parsing HTML...")

        base_url = 'https://www.property24.com'

        properties = []
        for card in cards:
            try:
                title_tag = card.select_one('.p24_title')
                title = title_tag.get_text(strip=True) if title_tag else 'N/A'

                price_tag = card.select_one('.p24_price')
                price_text = price_tag.get_text(strip=True).replace('R', '').replace(',', '').replace(' ', '')
                price = int(price_text) if price_text.isdigit() else 0

                desc_tag = card.select_one('.p24_excerpt')
                description = desc_tag.get_text(strip=True) if desc_tag else 'N/A'

                sqm_match = card.select_one('.p24_size')
                sqm_text = sqm_match.get_text(strip=True).replace(' ', '').replace('m&#xB2;', '').replace('m²', '')
                square_meters = int(sqm_text) if sqm_text.isdigit() else 0

                relative_url = card['href']
                property_url = base_url + relative_url

                if price > 0:
                    logger.debug(f"[Property24Scraper] price * usd_rate: {price * usd_rate_value}")
                    per_sqm = 0 if square_meters == 0 else round((price / square_meters) * usd_rate_value)
                    properties.append({
                        'title': title,
                        'description': description,
                        'price': price,
                        'price_in_USD': round(price * usd_rate_value),
                        'square_meter': square_meters,
                        'per_square_meter_in_USD': per_sqm,
                        'details_url': property_url,
                    })

            except Exception as e:
                logger.warning(f"⚠️ [Property24Scraper] Error parsing card: {e}")

        return properties
