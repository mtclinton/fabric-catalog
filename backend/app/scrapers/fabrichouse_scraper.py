"""
Scraper for Fabric House website (https://www.fabrichouse.com)
Handles both listing pages (with pagination) and individual product pages
"""
from .base_scraper import BaseScraper
from bs4 import BeautifulSoup
from typing import Dict, List
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import asyncio


class FabricHouseScraper(BaseScraper):
    """Scraper for Fabric House website"""
    
    async def scrape(self, url: str) -> Dict:
        """
        Scrape fabric information from Fabric House URL.
        
        If URL is a listing page, extracts all product URLs and scrapes them.
        If URL is a product page, scrapes the individual product.
        
        Returns dict with 'fabrics' key containing list of fabric dicts for listing pages,
        or single fabric dict for product pages.
        """
        # Check if this is a listing page
        if self._is_listing_page(url):
            return await self._scrape_listing_page(url)
        else:
            return await self._scrape_product_page(url)
    
    def _is_listing_page(self, url: str) -> bool:
        """Check if URL is a listing page (contains /all-fabrics/ or similar)"""
        return '/all-fabrics/' in url or '/search' in url or '?p=' in url
    
    async def _scrape_listing_page(self, url: str) -> Dict:
        """
        Scrape listing page and extract all product URLs from all pages.
        Returns dict with 'fabrics' key containing list of fabric data.
        """
        all_fabrics = []
        page = 1
        
        while True:
            # Build URL for current page
            page_url = self._build_page_url(url, page)
            print(f"Scraping page {page}: {page_url}")
            
            html = await self.fetch_html(page_url)
            if not html:
                break
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract product URLs from this page
            product_urls = self._extract_product_urls(soup, url)
            
            if not product_urls:
                print(f"No products found on page {page}, stopping pagination")
                break
            
            print(f"Found {len(product_urls)} products on page {page}")
            
            # Scrape each product page
            for product_url in product_urls:
                try:
                    fabric_data = await self._scrape_product_page(product_url)
                    if fabric_data and fabric_data.get('name') and fabric_data.get('name') != 'Unknown':
                        # Add the product URL to the fabric data so we can track it
                        fabric_data['url'] = product_url
                        all_fabrics.append(fabric_data)
                    # Small delay between product scrapes
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Error scraping product {product_url}: {e}")
                    continue
            
            # Check if there's a next page
            if not self._has_next_page(soup):
                break
            
            page += 1
            
            # Safety limit to prevent infinite loops
            if page > 100:
                print("Reached page limit (100), stopping")
                break
            
            # Delay between pages
            await asyncio.sleep(2)
        
        print(f"Total fabrics scraped: {len(all_fabrics)}")
        
        # Return special format for listing pages
        # The scheduled_scraper will need to handle this
        return {
            'fabrics': all_fabrics,
            'is_listing_page': True,
            'total_count': len(all_fabrics)
        }
    
    def _build_page_url(self, base_url: str, page: int) -> str:
        """Build URL for specific page number"""
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query)
        query_params['p'] = [str(page)]
        
        new_query = urlencode(query_params, doseq=True)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
    
    def _extract_product_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all product URLs from listing page"""
        product_urls = []
        
        # Look for product links - Fabric House uses various patterns
        # Try multiple selectors
        selectors = [
            'a[href*="/product/"]',
            'a[href*="/fabric/"]',
            'a[href*="/int/all-fabrics/"]',
            '.product-card a',
            '.product-item a',
            '[class*="product"] a[href]',
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    # Convert to absolute URL
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        parsed = urlparse(base_url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"
                    elif not href.startswith('http'):
                        href = urljoin(base_url, href)
                    
                    # Filter out listing pages and keep only product pages
                    if '/product/' in href or '/fabric/' in href:
                        if href not in product_urls and '?p=' not in href:
                            product_urls.append(href)
        
        # Fallback: look for product codes (F followed by digits) and try to find links
        if not product_urls:
            product_codes = soup.find_all(string=re.compile(r'F\d{6,10}'))
            for code_elem in product_codes:
                parent = code_elem.find_parent()
                if parent:
                    link = parent.find('a', href=True)
                    if link:
                        href = link.get('href')
                        if href:
                            if href.startswith('/'):
                                parsed = urlparse(base_url)
                                href = f"{parsed.scheme}://{parsed.netloc}{href}"
                            elif not href.startswith('http'):
                                href = urljoin(base_url, href)
                            if href not in product_urls:
                                product_urls.append(href)
        
        return list(set(product_urls))  # Remove duplicates
    
    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """Check if there's a next page available"""
        # Look for pagination indicators
        next_indicators = [
            soup.find('a', string=re.compile(r'Next|→|>', re.I)),
            soup.find('a', class_=re.compile(r'next', re.I)),
            soup.find('a', {'aria-label': re.compile(r'next', re.I)}),
        ]
        
        for indicator in next_indicators:
            if indicator and indicator.get('href'):
                return True
        
        # Check for page numbers
        page_links = soup.find_all('a', href=re.compile(r'[?&]p=\d+'))
        if page_links:
            # If we found page links, assume there might be more
            return True
        
        return False
    
    async def _scrape_product_page(self, url: str) -> Dict:
        """Scrape individual product page"""
        html = await self.fetch_html(url)
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        data = {}
        
        # Extract name
        name = self._extract_name(soup)
        if name:
            data['name'] = name
        
        # Extract price
        price = self._extract_price(soup)
        if price:
            data['price'] = price
            data['currency'] = 'EUR'  # Fabric House uses EUR
        
        # Extract composition/material
        composition = self._extract_composition(soup)
        if composition:
            data['composition'] = composition
        
        # Extract image URL - CRITICAL for image downloading
        image_url = self._extract_image_url(soup, url)
        if image_url:
            data['image_url'] = image_url
        
        # Extract other details
        description = self._extract_description(soup)
        if description:
            data['description'] = description
        
        width = self._extract_width(soup)
        if width:
            data['width'] = width
        
        weight = self._extract_weight(soup)
        if weight:
            data['weight'] = weight
        
        return data
    
    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract product name"""
        # Try h1 first
        h1 = soup.find('h1')
        if h1:
            name = self.clean_text(h1.get_text())
            if name and name != 'Unknown':
                return name
        
        # Try title tag
        title = soup.find('title')
        if title:
            name = self.clean_text(title.get_text())
            if '|' in name:
                name = name.split('|')[0].strip()
            if name and name != 'Unknown':
                return name
        
        # Look for product name in common classes
        name_selectors = [
            '.product-name',
            '.product-title',
            '[class*="product-name"]',
            '[class*="product-title"]',
        ]
        
        for selector in name_selectors:
            elem = soup.select_one(selector)
            if elem:
                name = self.clean_text(elem.get_text())
                if name and name != 'Unknown':
                    return name
        
        # Fallback: look for all-caps text that looks like a fabric name
        all_text = soup.get_text()
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
        for line in lines:
            if re.match(r'^[A-Z][A-Z\s,&\-\.()]+$', line) and len(line) > 15 and '%' not in line and '€' not in line:
                return line.strip()
        
        return 'Unknown'
    
    def _extract_price(self, soup: BeautifulSoup) -> float:
        """Extract price (for 1m to 5m range if available)"""
        text = soup.get_text()
        
        # Look for price pattern: "€21.90/m excl. VAT | 1m to 5m"
        price_patterns = [
            r'€(\d+[\.,]\d+)/m[^€]*?1m\s*to\s*5m',
            r'1m\s*to\s*5m[^€]*?€(\d+[\.,]\d+)',
            r'€(\d+[\.,]\d+)[^€]*?\|[^€]*?1m\s*to\s*5m',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                price_str = match.group(1).replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    pass
        
        # Fallback: get first price mentioned
        first_price = self.extract_price(text)
        if first_price:
            return first_price
        
        return None
    
    def _extract_composition(self, soup: BeautifulSoup) -> str:
        """Extract fabric composition"""
        text = soup.get_text()
        
        # Look for composition patterns
        composition_patterns = [
            r'(100%\s+(?:Virgin\s+)?(?:Wool|Cotton|Silk|Linen|Cashmere|Bamboo|Modal|Tencel|Viscose)[^€\n]*)',
            r'(\d+%\s+(?:Virgin\s+)?(?:Wool|Cotton|Silk|Linen|Cashmere)[^€\n]*)',
        ]
        
        for pattern in composition_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                composition = match.group(1).strip()
                composition = re.sub(r'\s+', ' ', composition)
                if len(composition) < 100:
                    return composition
        
        return None
    
    def _extract_image_url(self, soup: BeautifulSoup, base_url: str) -> str:
        """Extract product image URL - CRITICAL for image downloading"""
        # Try multiple selectors for product images
        img_selectors = [
            'img[src*="product"]',
            '.product-image img',
            '.product-photo img',
            'main img[src*="product"]',
            '[class*="product"] img',
            'img[itemprop="image"]',
            '.gallery img',
            'img[data-src*="product"]',
            'img[alt*="F"]',  # Fabric House product images often have F codes in alt
        ]
        
        for selector in img_selectors:
            img_elem = soup.select_one(selector)
            if img_elem:
                img_url = (img_elem.get('src') or 
                          img_elem.get('data-src') or 
                          img_elem.get('data-lazy-src') or
                          img_elem.get('data-original'))
                
                if img_url:
                    # Convert to absolute URL
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        parsed = urlparse(base_url)
                        img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                    elif not img_url.startswith('http'):
                        img_url = urljoin(base_url, img_url)
                    
                    # Filter out icons/logos
                    if any(skip in img_url.lower() for skip in ['icon', 'logo', 'avatar', 'badge', 'button']):
                        continue
                    
                    # Check size if available
                    width = img_elem.get('width')
                    height = img_elem.get('height')
                    if width and height:
                        try:
                            if int(width) < 100 or int(height) < 100:
                                continue
                        except:
                            pass
                    
                    return img_url
        
        # Fallback: get largest image
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
                img_url = urljoin(base_url, img_url)
            
            # Skip icons/logos
            if any(skip in img_url.lower() for skip in ['icon', 'logo', 'avatar']):
                continue
            
            # Estimate size
            width = img.get('width', '0')
            height = img.get('height', '0')
            try:
                size = int(width) * int(height) if width and height else 10000
                if size > largest_size:
                    largest_size = size
                    largest_img = img_url
            except:
                if not largest_img:
                    largest_img = img_url
        
        return largest_img if largest_img else None
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract product description"""
        desc_selectors = [
            '.product-description',
            '.description',
            '[class*="description"]',
        ]
        
        for selector in desc_selectors:
            elem = soup.select_one(selector)
            if elem:
                desc = self.clean_text(elem.get_text())
                if desc:
                    return desc
        
        return None
    
    def _extract_width(self, soup: BeautifulSoup) -> str:
        """Extract fabric width"""
        text = soup.get_text()
        width_match = re.search(r'Width[:\s]+(\d+\s*cm)', text, re.I)
        if width_match:
            return width_match.group(1)
        return None
    
    def _extract_weight(self, soup: BeautifulSoup) -> str:
        """Extract fabric weight"""
        text = soup.get_text()
        weight_match = re.search(r'Weight[:\s]+(\d+\s*g/m)', text, re.I)
        if weight_match:
            return weight_match.group(1)
        return None
