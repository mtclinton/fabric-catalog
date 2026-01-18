from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database will be stored in persistent volume
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/fabric_catalog.db")

# Ensure data directory exists and has proper permissions
if "sqlite" in DATABASE_URL:
    # Extract directory path from database URL
    if DATABASE_URL.startswith("sqlite:///./"):
        db_path = DATABASE_URL.replace("sqlite:///./", "")
    elif DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
    else:
        db_path = DATABASE_URL.replace("sqlite://", "")
    
    db_dir = os.path.dirname(db_path)
    if db_dir:
        # Create directory with full permissions
        os.makedirs(db_dir, mode=0o777, exist_ok=True)
        # Try to set permissions (may fail on some systems)
        try:
            os.chmod(db_dir, 0o777)
            # Also ensure parent directories are accessible
            parent = os.path.dirname(db_dir)
            if parent and os.path.exists(parent):
                os.chmod(parent, 0o777)
        except (OSError, PermissionError):
            pass

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
