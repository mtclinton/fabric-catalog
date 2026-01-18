from .base_scraper import BaseScraper
from bs4 import BeautifulSoup
from typing import Dict
import re
from urllib.parse import urljoin, urlparse


class GenericScraper(BaseScraper):
    """
    Generic scraper that tries to extract common patterns from any site.
    
    IMPORTANT: All scrapers must return 'image_url' in the data dictionary
    for images to be downloaded and displayed on the frontend.
    """
    
    async def scrape(self, url: str) -> Dict:
        """
        Scrape fabric information from URL.
        
        Returns dict with keys including:
        - name: Fabric name
        - price: Price as float
        - currency: Currency code (USD, EUR, GBP, etc.)
        - image_url: FULL URL to the fabric image (required for image download)
        - composition: Fiber composition
        - description: Product description
        - Other optional fields (width, color, pattern, etc.)
        """
        html = await self.fetch_html(url)
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        data = {}
        
        # Name
        title = soup.find('h1') or soup.find('title')
        if title:
            title_text = self.clean_text(title.get_text())
            if '|' in title_text:
                title_text = title_text.split('|')[0].strip()
            data['name'] = title_text
        
        # Price
        price_selectors = [
            '[class*="price"]',
            '[id*="price"]',
            '.product-price',
            '.price',
        ]
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = self.clean_text(price_elem.get_text())
                price = self.extract_price(price_text)
                if price:
                    data['price'] = price
                    if '$' in price_text:
                        data['currency'] = 'USD'
                    elif '£' in price_text:
                        data['currency'] = 'GBP'
                    elif '€' in price_text:
                        data['currency'] = 'EUR'
                    break
        
        # Image - CRITICAL: Must extract full image URL
        # Try multiple selectors to find product images
        img_selectors = [
            'img[src*="product"]',
            '.product-image img',
            '.product-photo img',
            'main img[src*="product"]',
            '[class*="product"] img',
            'img[itemprop="image"]',
            '.gallery img',
            'img[data-src*="product"]',  # Lazy-loaded images
        ]
        
        image_url = None
        for selector in img_selectors:
            img_elem = soup.select_one(selector)
            if img_elem:
                # Try multiple attributes for image URL
                img_url = (img_elem.get('src') or 
                          img_elem.get('data-src') or 
                          img_elem.get('data-lazy-src') or
                          img_elem.get('data-original'))
                
                if img_url:
                    # Convert relative URLs to absolute
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        # Absolute path from domain root
                        parsed = urlparse(url)
                        img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                    elif not img_url.startswith('http'):
                        # Relative URL
                        img_url = urljoin(url, img_url)
                    
                    # Filter out tiny icons/logos (usually < 100px)
                    # Check if it's likely a product image
                    width = img_elem.get('width')
                    height = img_elem.get('height')
                    if width and height:
                        try:
                            if int(width) < 100 or int(height) < 100:
                                continue
                        except:
                            pass
                    
                    # Skip common non-product images
                    if any(skip in img_url.lower() for skip in ['icon', 'logo', 'avatar', 'badge', 'button']):
                        continue
                    
                    image_url = img_url
                    break
        
        # If no product image found, try to get the largest image on the page
        if not image_url:
            all_images = soup.find_all('img')
            largest_img = None
            largest_size = 0
            
            for img in all_images:
                img_url = img.get('src') or img.get('data-src')
                if not img_url:
                    continue
                
                # Convert to absolute URL
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif not img_url.startswith('http'):
                    img_url = urljoin(url, img_url)
                
                # Skip icons/logos
                if any(skip in img_url.lower() for skip in ['icon', 'logo', 'avatar']):
                    continue
                
                # Estimate size from attributes or use as fallback
                width = img.get('width', '0')
                height = img.get('height', '0')
                try:
                    size = int(width) * int(height) if width and height else 10000
                    if size > largest_size:
                        largest_size = size
                        largest_img = img_url
                except:
                    if not largest_img:  # Use first valid image as fallback
                        largest_img = img_url
            
            if largest_img:
                image_url = largest_img
        
        if image_url:
            data['image_url'] = image_url
            print(f"Found image URL: {image_url}")
        else:
            print(f"Warning: No image found for {url}")
        
        # Description
        desc_elem = soup.select_one('[class*="description"]')
        if desc_elem:
            data['description'] = self.clean_text(desc_elem.get_text())
        
        # Composition
        all_text = soup.get_text()
        composition_match = re.search(r'(\d+%\s*(?:Wool|Cotton|Linen|Silk)[\s/]*)+', all_text, re.I)
        if composition_match:
            data['composition'] = self.clean_text(composition_match.group(0))
        
        return data
