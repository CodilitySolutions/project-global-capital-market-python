from bs4 import BeautifulSoup
import requests
from app.scrapers.base import BaseScraper
from app.settings.logger import logger
from pathlib import Path
from app.scrapers.utils import fallback_scraper

LOG_DIR = Path(__file__).resolve().parent.parent / "log"
LOG_DIR.mkdir(exist_ok=True)


class PrivatePropertyScraper(BaseScraper):
    def scrape(self, url: str, usd_rate: list, i: int) -> list:
        logger.info("🌐 [PrivatePropertyScraper] Fetching page...")

        try:
            usd_rate_value = float(usd_rate[0].split(',')[1].strip().split(' ')[0])
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            # response = requests.get(url, headers=headers, timeout=30)
            response = self.safe_request(url, headers)
            if response is None:
                fallback_scraper(url)
                # return []  # Indicates error to caller
            
            with open(LOG_DIR / f"scraped_{i + 1}.html", "w", encoding="utf-8") as file:
                file.write(response.text)
            logger.info(f"📂 [PrivatePropertyScraper] HTML content saved to {file_path}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"❌ [PrivatePropertyScraper] Failed to fetch HTML: {e}")
            return []

        logger.info("✅ [PrivatePropertyScraper] Page loaded. Parsing...")

        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('a.listing-result')
        base_url = 'https://www.privateproperty.co.za'
        properties = []

        for card in cards:
            try:
                title_tag = card.select_one('.listing-result__title')
                title = title_tag.get_text(strip=True) if title_tag else 'N/A'

                price_tag = card.select_one('.listing-result__price')
                price_text = price_tag.get_text(strip=True).replace('R', '').replace(' ', '').replace(' ', '')
                price = int(price_text) if price_text.isdigit() else 0

                desc_tag = card.select_one('.listing-result__description')
                description = desc_tag.get_text(strip=True) if desc_tag else 'N/A'

                size_spans = card.select('.listing-result__feature')
                square_meters = 0

                for span in size_spans:
                    title_attr = span.get('title', '')
                    if 'size' in title_attr.lower():
                        size_text = span.get_text(strip=True)
                        size_num = ''.join(filter(str.isdigit, size_text.split('m')[0].replace(' ', '')))
                        if size_num:
                            square_meters = int(size_num)
                        break

                relative_url = card['href']
                property_url = base_url + relative_url

                if price > 0:
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
                logger.warning(f"⚠️ [PrivatePropertyScraper] Error parsing card: {e}")

        return properties
