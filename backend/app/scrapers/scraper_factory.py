from urllib.parse import urlparse
from typing import Optional
from .base_scraper import BaseScraper
from .generic_scraper import GenericScraper


class ScraperFactory:
    """Factory to get appropriate scraper for a URL"""
    
    _scrapers = {
        'fabrichouse.com': None,  # Will be implemented
        # Add more site-specific scrapers here
    }
    
    @staticmethod
    def get_scraper(url: str) -> Optional[BaseScraper]:
        """Get the appropriate scraper for a given URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        
        # Check for exact domain match
        scraper_class = ScraperFactory._scrapers.get(domain)
        if scraper_class:
            return scraper_class()
        
        # Fall back to generic scraper
        return GenericScraper()
