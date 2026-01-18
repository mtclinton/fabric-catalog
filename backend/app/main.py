from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from urllib.parse import urlparse

from .database import SessionLocal, engine, Base
from .models import Fabric
from .schemas import FabricCreate, FabricResponse, ScrapeRequest, RatingUpdate
from .scrapers.scraper_factory import ScraperFactory
from .utils import download_image
from .scheduler import start_scheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fabric Catalog API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for images
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images")
os.makedirs(static_dir, exist_ok=True)
static_base = os.path.dirname(static_dir)
app.mount("/static", StaticFiles(directory=static_base), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"message": "Fabric Catalog API"}


@app.get("/api/fabrics", response_model=List[FabricResponse])
def get_fabrics(
    skip: int = 0,
    limit: int = 1000,
    rating: Optional[str] = None,
    origin: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all fabrics with pagination and optional filtering"""
    query = db.query(Fabric)
    
    if rating and rating != "all":
        query = query.filter(Fabric.rating == rating)
    
    if origin:
        query = query.filter(Fabric.origin.contains(origin))
    
    fabrics = query.offset(skip).limit(limit).all()
    return fabrics


@app.get("/api/fabrics/{fabric_id}", response_model=FabricResponse)
def get_fabric(fabric_id: int, db: Session = Depends(get_db)):
    """Get a specific fabric by ID"""
    fabric = db.query(Fabric).filter(Fabric.id == fabric_id).first()
    if not fabric:
        raise HTTPException(status_code=404, detail="Fabric not found")
    return fabric


@app.post("/api/fabrics/scrape", response_model=FabricResponse)
async def scrape_fabric(
    request: ScrapeRequest,
    db: Session = Depends(get_db)
):
    """Scrape fabric information from a URL"""
    existing = db.query(Fabric).filter(Fabric.url == request.url).first()
    if existing:
        return existing
    
    scraper = ScraperFactory.get_scraper(request.url)
    if not scraper:
        raise HTTPException(status_code=400, detail=f"No scraper available for URL: {request.url}")
    
    try:
        data = await scraper.scrape(request.url)
        
        # Handle listing pages that return multiple fabrics
        if data.get("is_listing_page") and data.get("fabrics"):
            # Return summary for listing pages
            fabrics_added = []
            for fabric_data in data['fabrics']:
                fabric_url = fabric_data.get('url', request.url)
                
                # Check if already exists
                existing = db.query(Fabric).filter(Fabric.url == fabric_url).first()
                if existing:
                    fabrics_added.append(existing)
                    continue
                
                parsed_url = urlparse(fabric_url)
                origin = parsed_url.netloc.replace('www.', '')
                
                image_path = None
                if fabric_data.get("image_url"):
                    image_path = await download_image(fabric_data["image_url"], fabric_data.get("name", "fabric"))
                
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
                db.refresh(fabric)
                fabrics_added.append(fabric)
            
            # Return the first fabric as representative
            if fabrics_added:
                return fabrics_added[0]
            else:
                raise HTTPException(status_code=400, detail="No fabrics found on listing page")
        
        # Handle single product page
        # Extract origin from URL
        parsed_url = urlparse(request.url)
        origin = parsed_url.netloc.replace('www.', '')
        
        # Download and save image if image_url is provided by scraper
        image_path = None
        if data.get("image_url"):
            print(f"Downloading image for {data.get('name', 'fabric')}...")
            image_path = await download_image(data["image_url"], data.get("name", "fabric"))
            if image_path:
                print(f"Image saved to {image_path}")
            else:
                print(f"Warning: Failed to download image from {data.get('image_url')}")
        else:
            print(f"Warning: No image_url returned by scraper for {request.url}")
        
        fabric = Fabric(
            name=data.get("name", "Unknown"),
            url=request.url,
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
        db.refresh(fabric)
        
        return fabric
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@app.post("/api/fabrics/scrape-batch")
async def scrape_fabric_batch(
    urls: List[str],
    db: Session = Depends(get_db)
):
    """Scrape multiple fabric URLs"""
    results = []
    errors = []
    
    for url in urls:
        try:
            existing = db.query(Fabric).filter(Fabric.url == url).first()
            if existing:
                results.append({"url": url, "status": "exists", "id": existing.id})
                continue
            
            scraper = ScraperFactory.get_scraper(url)
            if not scraper:
                errors.append({"url": url, "error": "No scraper available"})
                continue
            
            data = await scraper.scrape(url)
            
            parsed_url = urlparse(url)
            origin = parsed_url.netloc.replace('www.', '')
            
            image_path = None
            if data.get("image_url"):
                image_path = await download_image(data["image_url"], data.get("name", "fabric"))
            
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
            db.refresh(fabric)
            
            results.append({"url": url, "status": "success", "id": fabric.id})
        except Exception as e:
            errors.append({"url": url, "error": str(e)})
    
    return {"results": results, "errors": errors, "total": len(urls)}


@app.patch("/api/fabrics/{fabric_id}/rating", response_model=FabricResponse)
def update_fabric_rating(
    fabric_id: int,
    rating_update: RatingUpdate,
    db: Session = Depends(get_db)
):
    """Update fabric rating"""
    if rating_update.rating not in ["yes", "no", "maybe", "unrated"]:
        raise HTTPException(status_code=400, detail="Rating must be 'yes', 'no', 'maybe', or 'unrated'")
    
    fabric = db.query(Fabric).filter(Fabric.id == fabric_id).first()
    if not fabric:
        raise HTTPException(status_code=404, detail="Fabric not found")
    
    fabric.rating = rating_update.rating
    db.commit()
    db.refresh(fabric)
    
    return fabric


@app.get("/api/fabrics/stats")
def get_fabric_stats(db: Session = Depends(get_db)):
    """Get statistics about fabrics"""
    total = db.query(Fabric).count()
    yes_count = db.query(Fabric).filter(Fabric.rating == "yes").count()
    no_count = db.query(Fabric).filter(Fabric.rating == "no").count()
    maybe_count = db.query(Fabric).filter(Fabric.rating == "maybe").count()
    unrated_count = db.query(Fabric).filter(Fabric.rating == "unrated").count()
    
    origins = db.query(Fabric.origin).distinct().all()
    origin_list = [o[0] for o in origins if o[0]]
    
    return {
        "total": total,
        "ratings": {
            "yes": yes_count,
            "no": no_count,
            "maybe": maybe_count,
            "unrated": unrated_count
        },
        "origins": origin_list
    }


@app.delete("/api/fabrics/{fabric_id}")
def delete_fabric(fabric_id: int, db: Session = Depends(get_db)):
    """Delete a fabric"""
    fabric = db.query(Fabric).filter(Fabric.id == fabric_id).first()
    if not fabric:
        raise HTTPException(status_code=404, detail="Fabric not found")
    
    if fabric.image_path and os.path.exists(fabric.image_path):
        os.remove(fabric.image_path)
    
    db.delete(fabric)
    db.commit()
    return {"message": "Fabric deleted"}


@app.on_event("startup")
async def startup_event():
    """Start scheduler when app starts"""
    start_scheduler()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
