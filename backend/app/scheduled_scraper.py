"""
Scheduled scraper that runs daily to update fabric information
"""
import asyncio
import os
import json
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Fabric
from .scrapers.scraper_factory import ScraperFactory
from .utils import download_image
from datetime import datetime
from urllib.parse import urlparse


async def scrape_all_bookmarks():
    """Scrape all URLs from the config file"""
    db: Session = SessionLocal()
    
    try:
        # Read URLs from config file (mounted in container)
        config_file = "/app/fabric-config.json"
        
        if not os.path.exists(config_file):
            print(f"Config file not found: {config_file}")
            return
        
        # Load URLs from JSON config file
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        urls = config.get("urls", [])
        
        if not urls:
            print("No URLs found in config file")
            return
        
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
                    # Create new fabric(s)
                    scraper = ScraperFactory.get_scraper(url)
                    if not scraper:
                        print(f"No scraper for: {url}")
                        continue
                    
                    data = await scraper.scrape(url)
                    
                    # Handle listing pages that return multiple fabrics
                    if data.get("is_listing_page") and data.get("fabrics"):
                        print(f"Processing listing page with {len(data['fabrics'])} fabrics")
                        for fabric_data in data['fabrics']:
                            # Use the product URL from the fabric data if available, otherwise use original URL
                            fabric_url = fabric_data.get('url', url)
                            
                            # Check if this fabric already exists
                            existing = db.query(Fabric).filter(Fabric.url == fabric_url).first()
                            
                            if existing:
                                # Update existing fabric
                                if fabric_data.get("name"):
                                    existing.name = fabric_data.get("name")
                                if fabric_data.get("price"):
                                    existing.price = fabric_data.get("price")
                                if fabric_data.get("composition"):
                                    existing.composition = fabric_data.get("composition")
                                
                                if fabric_data.get("image_url") and not existing.image_path:
                                    print(f"Downloading image for existing fabric {existing.name}...")
                                    image_path = await download_image(fabric_data["image_url"], existing.name)
                                    if image_path:
                                        existing.image_path = image_path
                                
                                existing.last_scraped = datetime.now()
                                db.commit()
                                print(f"Updated: {fabric_url}")
                            else:
                                # Create new fabric from listing page data
                                parsed_url = urlparse(fabric_url)
                                origin = parsed_url.netloc.replace('www.', '')
                                
                                image_path = None
                                if fabric_data.get("image_url"):
                                    print(f"Downloading image for {fabric_data.get('name', 'fabric')}...")
                                    image_path = await download_image(fabric_data["image_url"], fabric_data.get("name", "fabric"))
                                    if image_path:
                                        print(f"Image saved: {image_path}")
                                
                                fabric = Fabric(
                                    name=fabric_data.get("name", "Unknown"),
                                    url=fabric_url,
                                    origin=origin,
                                    rating="unrated",
                                    price=fabric_data.get("price"),
                                    currency=fabric_data.get("currency", "EUR"),
                                    composition=fabric_data.get("composition"),
                                    description=fabric_data.get("description"),
                                    image_path=image_path,
                                    width=fabric_data.get("width"),
                                    care_instructions=fabric_data.get("care_instructions"),
                                    color=fabric_data.get("color"),
                                    pattern=fabric_data.get("pattern"),
                                    weight=fabric_data.get("weight"),
                                    brand=fabric_data.get("brand"),
                                    extra_info=fabric_data.get("extra_info"),
                                )
                                
                                db.add(fabric)
                                db.commit()
                                print(f"Added: {fabric_url}")
                        
                        # Skip the normal processing for listing pages
                        continue
                    
                    # Handle single product page
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
