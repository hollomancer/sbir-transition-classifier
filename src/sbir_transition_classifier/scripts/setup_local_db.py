#!/usr/bin/env python3
"""
Local database setup script for SBIR transition classifier.

This script uses SQLAlchemy to create the project's schema on the target
database engine instead of emitting raw SQL via sqlite3. It avoids manipulating
sys.path and imports the package modules directly.

Usage:
    # Use configured default DB URL (from pydantic settings in package)
    python scripts/setup_local_db.py

    # Provide a custom SQLAlchemy URL
    python scripts/setup_local_db.py --db-url sqlite:///./data/local.db
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Import package models / settings
from sbir_transition_classifier.core import models
from sbir_transition_classifier.db.config import get_database_config


def _ensure_sqlite_dirs(db_url: str) -> None:
    """
    Ensure parent directories for local sqlite file exist when given a sqlite URL.
    This accepts forms like:
      - sqlite:///relative/path/to/db.db
      - sqlite:////absolute/path/to/db.db
    """
    if not db_url.startswith("sqlite"):
        return

    # Trim prefix (handle 3 or 4 slashes)
    path = db_url.split("sqlite://", 1)[1]
    # Remove a leading slash from relative URLs created with triple slashes
    if path.startswith("/"):
        # for sqlite:///relative/path -> path starts with /
        # but we want to treat triple-slash as relative to cwd only when three slashes used.
        # Simpler: treat the remaining string as a filesystem path possibly starting with /
        file_path = Path(path)
    else:
        file_path = Path(path)

    parent = file_path.parent
    if str(parent) and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created parent directory for sqlite DB: {parent}")


def _make_engine(db_url: str):
    """
    Create a SQLAlchemy engine appropriate for the URL. For SQLite, set
    check_same_thread=False and use NullPool to avoid forking/pooling issues.
    """
    if db_url.startswith("sqlite"):
        # Ensure directory exists for file-based sqlite
        _ensure_sqlite_dirs(db_url)
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
            pool_pre_ping=True,
        )
    else:
        engine = create_engine(
            db_url, pool_size=10, max_overflow=20, pool_pre_ping=True
        )
    return engine


@click.command()
@click.option(
    "--db-url",
    default=None,
    help="SQLAlchemy database URL to initialize. If omitted, uses package default.",
)
def main(db_url: Optional[str]):
    """Create database schema using SQLAlchemy metadata."""
    # Configure loguru to print to console
    logger.remove()
    logger.add(lambda msg: click.echo(msg, err=False), level="INFO")

    # Get database URL from unified config system
    if db_url:
        target_url = db_url
    else:
        db_config = get_database_config()
        target_url = db_config.url
    logger.info(f"Initializing database for URL: {target_url}")

    try:
        engine = _make_engine(target_url)

        # Create all tables using the package's Base metadata
        # models.Base is the ORM base imported from sbir_transition_classifier.core.models
        models.Base.metadata.create_all(bind=engine)

        logger.info("Database schema created successfully.")
        click.echo(f"✅ Database initialized at: {target_url}")

    except Exception as exc:  # pragma: no cover - operational error handling
        logger.error(f"Failed to initialize database: {exc}")
        click.echo(f"❌ Database setup failed: {exc}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
