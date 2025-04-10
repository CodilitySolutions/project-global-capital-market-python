from abc import ABC, abstractmethod

class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, url: str, usd_rate: list, index: int) -> list:
        pass
