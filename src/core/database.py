# ============================================================
#  DATABASE - SQLAlchemy setup with SQLite
# ============================================================

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from src.core.config import config
from src.core.logger import logger

# Create engine for SQLite
engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for models
Base = declarative_base()

# Metadata for creating tables
metadata = MetaData()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Database session context manager.
    Usage:
        with get_db() as db:
            db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def init_database():
    """Create all tables if they don't exist"""
    logger.info("Initializing database...")
    
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


def get_engine():
    """Get database engine (for direct queries)"""
    return engine


__all__ = [
    'Base', 
    'metadata', 
    'get_db', 
    'init_database', 
    'engine',
    'SessionLocal'
]