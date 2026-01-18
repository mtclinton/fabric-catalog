from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from .database import Base


class Fabric(Base):
    __tablename__ = "fabrics"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    url = Column(String, unique=True, nullable=False, index=True)
    origin = Column(String, nullable=True, index=True)  # Website domain
    rating = Column(String, default="unrated", index=True)  # "yes", "no", "maybe", "unrated"
    price = Column(Float, nullable=True)
    currency = Column(String, default="USD")
    composition = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)  # Kept for backwards compatibility (first image)
    image_paths = Column(JSON, nullable=True)  # Array of image paths for multiple images
    width = Column(String, nullable=True)
    care_instructions = Column(Text, nullable=True)
    color = Column(String, nullable=True)
    pattern = Column(String, nullable=True)
    weight = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    extra_info = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_scraped = Column(DateTime(timezone=True), server_default=func.now())
