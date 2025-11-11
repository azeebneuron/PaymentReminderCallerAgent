"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from config.settings import settings
from database.models import Base
from utils.logger import logger


# Create database engine
engine = create_engine(
    settings.database_url,
    echo=not settings.is_production,  # Log SQL in development
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """Initialize database tables."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup.
    
    Usage:
        with get_db() as db:
            db.query(Client).all()
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


def get_db_session() -> Session:
    """
    Get database session (for FastAPI dependency injection).
    
    Usage:
        @app.get("/")
        def endpoint(db: Session = Depends(get_db_session)):
            pass
    """
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let FastAPI handle it