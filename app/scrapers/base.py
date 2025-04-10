from abc import ABC, abstractmethod
import requests
class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, url: str, usd_rate: list, index: int) -> list:
        pass

    def safe_request(self, url, headers, timeout=30):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None