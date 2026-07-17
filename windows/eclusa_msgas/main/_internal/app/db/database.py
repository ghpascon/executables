import csv
import logging
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional, Union

from fastapi import Response
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeMeta, sessionmaker
from sqlalchemy.pool import NullPool


from .session import Base

from app.core.settings import settings

# Constants
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_REPORT_FILENAME = "report.zip"

# Database driver mappings
SYNC_DRIVER_MAPPING = {
    "mysql": "pymysql",
    "postgresql": "psycopg2",
    "sqlite": None,
}


class DatabaseEngine:
    """
    Database engine manager for handling both sync and async database operations.

    This class manages SQLAlchemy engines, sessions, and provides utilities for
    database operations like clearing old records and generating reports.
    """

    def __init__(self) -> None:
        """Initialize DatabaseEngine with default values and attempt to connect."""
        self.database_url: Optional[str] = None
        self.sync_url: Optional[str] = None
        self.sync_engine = None
        self.async_engine = None
        self.SessionLocal = None

        result = self._initialize_engines_and_session()
        if isinstance(result, dict) and "error" in result:
            logging.error(f"[DatabaseEngine.__init__] Failed to initialize: {result['error']}")

    def _load_database_url(self) -> Optional[str]:
        try:
            url = settings.actions_data.get("DATABASE_URL")
            if not url:
                logging.error(
                    "[DatabaseEngine._load_database_url] 'DATABASE_URL' is None"
                )
                return None

            return url
        except Exception as e:
            logging.error(
                f"[DatabaseEngine._load_database_url] Unexpected error loading DATABASE_URL: {e}"
            )
            return None

    def _initialize_engines_and_session(self) -> Union[bool, Dict[str, str]]:
        """
        Initialize database engines and session factory.

        Returns:
            True if successful, dict with error message if failed
        """
        try:
            self.database_url = self._load_database_url()
            if not self.database_url:
                msg = "Invalid or missing database URL. Initialization postponed."
                logging.error(f"[DatabaseEngine._initialize_engines_and_session] {msg}")
                return {"error": msg}

            # Parse database dialect and driver
            dialect_plus_driver = self.database_url.split("://")[0]
            if "+" in dialect_plus_driver:
                dialect, async_driver = dialect_plus_driver.split("+")
            else:
                dialect = dialect_plus_driver
                async_driver = None

            # Get corresponding sync driver
            default_sync_driver = SYNC_DRIVER_MAPPING.get(dialect, None)

            # Build sync URL
            if default_sync_driver:
                self.sync_url = self.database_url.replace(
                    f"+{async_driver}", f"+{default_sync_driver}"
                )
            else:
                self.sync_url = self.database_url.replace(f"+{async_driver}", "")

            # Create sync engine
            self.sync_engine = create_engine(self.sync_url, echo=False)

            # Create async engine with appropriate configuration
            if dialect == "sqlite":
                # SQLite does not support pool parameters
                self.async_engine = create_async_engine(
                    self.database_url, echo=False, poolclass=NullPool
                )
            else:
                self.async_engine = create_async_engine(
                    self.database_url,
                    echo=False,
                    pool_size=DEFAULT_POOL_SIZE,
                    max_overflow=DEFAULT_MAX_OVERFLOW,
                    pool_pre_ping=True,
                )

            # Create session factory
            self.SessionLocal = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
            )

            self.create_tables()
            logging.info(
                "[DatabaseEngine._initialize_engines_and_session] Engine and session initialization successful."
            )
            return True

        except Exception as e:
            logging.error(
                f"[DatabaseEngine._initialize_engines_and_session] Failed to initialize engines and session: {e}"
            )
            self._reset_engines()
            return {"error": str(e)}

    def _reset_engines(self) -> None:
        """Reset all engine and session attributes to None."""
        self.database_url = None
        self.sync_url = None
        self.sync_engine = None
        self.async_engine = None
        self.SessionLocal = None

    def create_tables(self) -> None:
        """
        Create database tables if they don't exist.

        Uses sync engine to create tables. Logs errors but doesn't raise exceptions.
        """
        if self.sync_engine is None:
            logging.error(
                "[DatabaseEngine.create_tables] Sync engine not initialized. Skipping table creation."
            )
            return

        try:
            Base.metadata.create_all(bind=self.sync_engine)
            logging.info("[DatabaseEngine.create_tables] Tables created or already exist.")
        except Exception as e:
            logging.error(f"[DatabaseEngine.create_tables] Error creating tables: {e}")
            # Don't raise exception to allow application to continue

    def reload_database_url(self, new_url: str) -> Union[bool, Dict[str, str]]:
        """
        Reload database configuration with a new URL.

        Args:
            new_url: New database URL to use

        Returns:
            True if successful, dict with error message if failed
        """
        try:
            self.database_url = new_url
            result = self._initialize_engines_and_session()
            if result is True:
                logging.info(
                    "[DatabaseEngine.reload_database_url] Database URL reloaded successfully."
                )
                return True
            else:
                # result contains the dict {"error": ...}
                logging.error(f"[DatabaseEngine.reload_database_url] {result['error']}")
                return result
        except Exception as e:
            logging.error(f"[DatabaseEngine.reload_database_url] Error reloading DATABASE_URL: {e}")
            return {"error": str(e)}

    @asynccontextmanager
    async def get_db(self):
        """
        Async context manager for database sessions.
        Ensures rollback on exceptions and proper cleanup.

        Yields:
            AsyncSession instance
        """
        if self.SessionLocal is None:
            logging.error("[DatabaseEngine.get_db] Session not initialized.")
            raise RuntimeError("Database session factory not initialized.")

        db: AsyncSession = self.SessionLocal()
        try:
            yield db
            # Commit if no exceptions occurred
            await db.commit()
        except Exception as e:
            # Rollback in case of errors
            await db.rollback()
            logging.exception(f"[DatabaseEngine.get_db] Exception occurred, rolled back: {e}")
            raise  # Re-raise the exception so callers can handle it
        finally:
            # Close session to release connection
            await db.close()
    async def clear_db(self, days: int) -> Dict[str, Any]:
        """
        Clear old records from database tables.

        Args:
            days: Number of days to keep (older records will be deleted)

        Returns:
            Dict with success status and deleted tables list, or error message
        """
        if self.SessionLocal is None:
            logging.error("[DatabaseEngine.clear_db] Session not initialized, operation ignored.")
            return {"error": "Session not initialized"}

        try:
            async with self.get_db() as db:
                if db is None:
                    logging.error(
                        "[DatabaseEngine.clear_db] Session returned None, operation aborted."
                    )
                    return {"error": "Session returned None"}

                # Calculate cutoff date
                limit_date = datetime.now(timezone.utc) - timedelta(days=days)
                limit_date = limit_date.replace(hour=0, minute=0, second=0, microsecond=0)

                deleted_tables: List[str] = []

                # Clear records from all tables with timestamp column
                for cls in Base.__subclasses__():
                    if isinstance(cls, DeclarativeMeta) and hasattr(cls, "timestamp"):
                        try:
                            stmt = delete(cls).where(cls.timestamp < limit_date)
                            await db.execute(stmt)
                            deleted_tables.append(cls.__tablename__)
                        except Exception as table_exc:
                            logging.error(
                                f"[DatabaseEngine.clear_db] Failed to clear table '{cls.__tablename__}': {table_exc}"
                            )

                await db.commit()
                logging.info(
                    f"[DatabaseEngine.clear_db] Old records deleted up to {limit_date.isoformat()} from tables: {deleted_tables}"
                )
                return {"success": True, "deleted_tables": deleted_tables}

        except Exception as e:
            logging.error(f"[DatabaseEngine.clear_db] Error while clearing database: {e}")
            return {"error": str(e)}

    async def get_report(self) -> Union[StreamingResponse, Response]:
        """
        Generate a ZIP file containing CSV exports of all database tables.

        Returns:
            StreamingResponse with ZIP file or Response with error message
        """
        try:
            async with self.get_db() as db:
                if db is None:
                    logging.error("[DatabaseEngine.get_report] Database session not available")
                    return Response(content="Database session unavailable", status_code=503)

                zip_buffer = BytesIO()
                table_count = 0
                exported_tables: List[str] = []

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    # Export all database tables
                    for cls in Base.__subclasses__():
                        if isinstance(cls, DeclarativeMeta):
                            table_name = getattr(cls, "__tablename__", cls.__name__)
                            try:
                                logging.info(
                                    f"[DatabaseEngine.get_report] Processing table: {table_name}"
                                )
                                result = await db.execute(select(cls))
                                rows = result.scalars().all()

                                # Create CSV content
                                csv_buffer = StringIO()
                                writer = csv.writer(csv_buffer)

                                # Write header
                                headers = [col.name for col in cls.__table__.columns]
                                writer.writerow(headers)

                                # Write data rows
                                for row in rows:
                                    writer.writerow(
                                        [getattr(row, col.name) for col in cls.__table__.columns]
                                    )

                                # Add CSV to ZIP
                                csv_buffer.seek(0)
                                zip_file.writestr(f"{table_name}.csv", csv_buffer.read())

                                logging.info(
                                    f"[DatabaseEngine.get_report] Exported {len(rows)} rows from table: {table_name}"
                                )
                                table_count += 1
                                exported_tables.append(table_name)

                            except Exception as table_error:
                                logging.error(
                                    f"[DatabaseEngine.get_report] Failed to export table {table_name}: {table_error}"
                                )

                if table_count == 0:
                    logging.info(
                        "[DatabaseEngine.get_report] No tables were exported. ZIP will be empty."
                    )

                zip_buffer.seek(0)
                logging.info(
                    f"[DatabaseEngine.get_report] Report generation completed. {table_count} tables exported: {exported_tables}"
                )

                return StreamingResponse(
                    zip_buffer,
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename={DEFAULT_REPORT_FILENAME}"
                    },
                )

        except Exception as e:
            logging.error(f"[DatabaseEngine.get_report] Failed to generate reports: {e}")
            return Response(content=f"Failed to get reports: {str(e)}", status_code=500)


database_engine = DatabaseEngine()
