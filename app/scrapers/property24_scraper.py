from bs4 import BeautifulSoup
import requests
from app.scrapers.base import BaseScraper

class Property24Scraper(BaseScraper):
    def scrape(self, url: str, usd_rate: list, i: int) -> list:
        print("\n🤖 function fetch_properties_property24 started ...")
        print("Fetching page...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            file_path = f"scraped_{i + 1}.html"
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(response.text)
            print(f"📂 HTML content saved to {file_path}")
            response.raise_for_status()  # Raise an error for bad status codes
        except Exception as e:
            print("❌ Failed to fetch HTML.", e)
            return []

        print("✅ Page loaded. Parsing...")
        soup = BeautifulSoup(response.text, 'html.parser')

        # Get all cards that are likely to be properties
        cards = soup.select('a.p24_content')  # More general selector

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
                    usd_rate_value = float(usd_rate[0].split(',')[1].strip().split(' ')[0])  # Extract the numeric value from the list
                    print(f"price * usd_rate: {price * usd_rate_value}")
                    # print(f"((price/square_meters)*usd_rate): {(price/square_meters)*usd_rate_value}")
                    per_sqm = 0 if square_meters == 0 else round((price/square_meters)*usd_rate_value)
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
                print(f"⚠️ Error parsing card: {e}")

        return properties
