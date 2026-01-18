from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FabricBase(BaseModel):
    name: str
    url: str
    origin: Optional[str] = None
    rating: Optional[str] = "unrated"
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    composition: Optional[str] = None
    description: Optional[str] = None
    image_path: Optional[str] = None  # Kept for backwards compatibility
    image_paths: Optional[List[str]] = None  # Array of image paths
    width: Optional[str] = None
    care_instructions: Optional[str] = None
    color: Optional[str] = None
    pattern: Optional[str] = None
    weight: Optional[str] = None
    brand: Optional[str] = None
    extra_info: Optional[str] = None


class FabricCreate(FabricBase):
    pass


class FabricResponse(FabricBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_scraped: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ScrapeRequest(BaseModel):
    url: str


class RatingUpdate(BaseModel):
    rating: str  # "yes", "no", "maybe", "unrated"
