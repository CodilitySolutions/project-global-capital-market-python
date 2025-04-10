import requests
from bs4 import BeautifulSoup
import json

def fetch_properties_privateproperty(url, usd_rate, i):
    print("Fetching page...")
    try:
        usd_rate_value = float(usd_rate[0].split(',')[1].strip().split(' ')[0])  # Extract the numeric value from the list
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
    cards = soup.select('a.listing-result')  # More general selector

    base_url = 'https://www.privateproperty.co.za'

    properties = []
    for card in cards:
        try:
            # print('------------============= card ----=============: ')
            title_tag = card.select_one('.listing-result__title')
            title = title_tag.get_text(strip=True) if title_tag else 'N/A'
            # print('title',title)

            price_tag = card.select_one('.listing-result__price')
            # print('------------=========  price_tag   ------------=========  : ', price_tag)
            price_text = price_tag.get_text(strip=True).replace('R', '').replace(' ', '').replace(' ', '')
            # print('------------=========  price_text   ------------=========  : ', price_text)
            price = int(price_text) if price_text.isdigit() else 0
            # print('price',price)


            desc_tag = card.select_one('.listing-result__description')
            description = desc_tag.get_text(strip=True) if desc_tag else 'N/A'
            # print('description: ', description)

            size_spans = card.select('.listing-result__feature')
            square_meters = 0
            
            for span in size_spans:
                # print('------------=========  span   ------------=========  : ', span)
                title_attr = span.get('title', '')
                if 'size' in title_attr.lower():  # Looks for either "Land size" or "Floor size"
                    size_text = span.get_text(strip=True)
                    # Extract numbers only (handles formats like "4 253 m²")
                    size_num = ''.join(filter(str.isdigit, size_text.split('m')[0].replace(' ', '')))
                    if size_num:
                        square_meters = int(size_num)
                    break
            
            # print('square_meters',square_meters)
            relative_url = card['href']
            property_url = base_url + relative_url
            # print('property_url',property_url)

            if price > 0:
                # print(f"price * usd_rate: {price * usd_rate_value}")
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
