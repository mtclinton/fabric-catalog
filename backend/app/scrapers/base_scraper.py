from abc import ABC, abstractmethod
from typing import Dict, Optional
from bs4 import BeautifulSoup
import aiohttp
import re


class BaseScraper(ABC):
    """Base class for all fabric scrapers"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        return await response.text()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None
    
    def extract_price(self, text: str) -> Optional[float]:
        """Extract price from text"""
        if not text:
            return None
        patterns = [
            r'[\$£€]?\s*(\d+[\.,]\d{2})',
            r'(\d+[\.,]\d{2})\s*(USD|EUR|GBP)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text.replace(',', ''))
            if match:
                try:
                    return float(match.group(1).replace(',', '.'))
                except:
                    pass
        return None
    
    def clean_text(self, text: str) -> Optional[str]:
        """Clean and normalize text"""
        if not text:
            return None
        return ' '.join(text.split()).strip()
    
    @abstractmethod
    async def scrape(self, url: str) -> Dict:
        """Scrape fabric information from URL"""
        pass
