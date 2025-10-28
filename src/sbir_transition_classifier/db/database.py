"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .config import get_db_config_singleton

# Load database configuration
db_config = get_db_config_singleton()

# Create engine based on configuration
if db_config.url.startswith("sqlite"):
    engine = create_engine(
        db_config.url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=db_config.echo,
    )
else:
    # PostgreSQL, MySQL, etc.
    engine = create_engine(
        db_config.url,
        pool_size=db_config.pool_size,
        pool_timeout=db_config.pool_timeout,
        echo=db_config.echo,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
