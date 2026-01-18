"""
Scheduled scraper that runs daily to update fabric information
"""
import asyncio
import os
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Fabric
from .scrapers.scraper_factory import ScraperFactory
from .utils import download_image
from datetime import datetime
from urllib.parse import urlparse


async def scrape_all_bookmarks():
    """Scrape all URLs from the bookmarks file"""
    db: Session = SessionLocal()
    
    try:
        # Read URLs from bookmarks file (mounted in container)
        bookmarks_file = "/app/fabric-bookmarks.txt"
        
        if not os.path.exists(bookmarks_file):
            print(f"Bookmarks file not found: {bookmarks_file}")
            return
        
        urls = []
        with open(bookmarks_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('http'):
                    urls.append(line)
        
        print(f"Found {len(urls)} URLs to scrape")
        
        for url in urls:
            try:
                # Check if fabric already exists
                existing = db.query(Fabric).filter(Fabric.url == url).first()
                
                if existing:
                    # Update existing fabric
                    scraper = ScraperFactory.get_scraper(url)
                    if scraper:
                        data = await scraper.scrape(url)
                        
                        # Update fields if new data is available
                        if data.get("name"):
                            existing.name = data.get("name")
                        if data.get("price"):
                            existing.price = data.get("price")
                        if data.get("composition"):
                            existing.composition = data.get("composition")
                        
                        # Update image if new one is available
                        if data.get("image_url") and not existing.image_path:
                            print(f"Downloading image for existing fabric {existing.name}...")
                            image_path = await download_image(data["image_url"], existing.name)
                            if image_path:
                                existing.image_path = image_path
                                print(f"Image saved: {image_path}")
                        
                        existing.last_scraped = datetime.now()
                        db.commit()
                        print(f"Updated: {url}")
                else:
                    # Create new fabric
                    scraper = ScraperFactory.get_scraper(url)
                    if not scraper:
                        print(f"No scraper for: {url}")
                        continue
                    
                    data = await scraper.scrape(url)
                    
                    parsed_url = urlparse(url)
                    origin = parsed_url.netloc.replace('www.', '')
                    
                    # Download image if available
                    image_path = None
                    if data.get("image_url"):
                        print(f"Downloading image for {data.get('name', 'fabric')}...")
                        image_path = await download_image(data["image_url"], data.get("name", "fabric"))
                        if image_path:
                            print(f"Image saved: {image_path}")
                    else:
                        print(f"No image URL found for {url}")
                    
                    fabric = Fabric(
                        name=data.get("name", "Unknown"),
                        url=url,
                        origin=origin,
                        rating="unrated",
                        price=data.get("price"),
                        currency=data.get("currency", "USD"),
                        composition=data.get("composition"),
                        description=data.get("description"),
                        image_path=image_path,
                        width=data.get("width"),
                        care_instructions=data.get("care_instructions"),
                        color=data.get("color"),
                        pattern=data.get("pattern"),
                        weight=data.get("weight"),
                        brand=data.get("brand"),
                        extra_info=data.get("extra_info"),
                    )
                    
                    db.add(fabric)
                    db.commit()
                    print(f"Added: {url}")
                
                # Small delay to avoid overwhelming servers
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue
        
        print("Scraping completed!")
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(scrape_all_bookmarks())
