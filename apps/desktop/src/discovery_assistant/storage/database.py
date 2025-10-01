"""
SQLAlchemy database models and initialization for Discovery Assistant.

Handles database creation, schema setup, and ORM operations.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func

from .app_paths import get_database_path, initialize_file_structure

_LOGGER = logging.getLogger('DISCOVERY.database')

# SQLAlchemy setup
Base = declarative_base()
engine = None
SessionLocal = None


# Models
class Respondent(Base):
    """Respondent profile information (single instance)"""
    __tablename__ = 'respondent'

    id = Column(Integer, primary_key=True)
    full_name = Column(String(255))
    work_email = Column(String(255))
    department = Column(String(255))
    role_title = Column(String(255))
    primary_responsibilities = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrgMap(Base):
    """Organization mapping information (single instance)"""
    __tablename__ = 'org_map'

    id = Column(Integer, primary_key=True)
    reports_to = Column(String(255))
    peer_teams = Column(Text)
    downstream_consumers = Column(Text)
    org_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Process(Base):
    """Business processes (multiple instances)"""
    __tablename__ = 'processes'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    priority_rank = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    time_allocation_id = Column(Integer, nullable=True)  # Link to time allocation


class PainPoint(Base):
    """Pain points (multiple instances)"""
    __tablename__ = 'pain_points'

    id = Column(Integer, primary_key=True)
    pain_name = Column(String(255), nullable=False)
    priority_rank = Column(Integer)
    impact = Column(Float)
    frequency = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    estimated_time_weekly = Column(Integer, nullable=True)  # Hours per week
    time_allocation_id = Column(Integer, nullable=True)  # Link to time allocation


class DataSource(Base):
    """Data sources (multiple instances)"""
    __tablename__ = 'data_sources'

    id = Column(Integer, primary_key=True)
    source_name = Column(String(255), nullable=False)
    priority_rank = Column(Integer)
    connection_type = Column(String(100))
    description = Column(Text)
    configuration = Column(Text)  # JSON for flexible config storage
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Compliance(Base):
    """Compliance requirements (single instance with requirements as separate table later)"""
    __tablename__ = 'compliance'

    id = Column(Integer, primary_key=True)
    industry_sector = Column(String(255))
    geographic_scope = Column(String(255))
    business_activities = Column(Text)
    data_types_handled = Column(Text)
    third_party_vendors = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceRequirement(Base):
    """Individual compliance requirements (multiple instances)"""
    __tablename__ = 'compliance_requirements'

    id = Column(Integer, primary_key=True)
    requirement_name = Column(String(255), nullable=False)
    priority_rank = Column(Integer, nullable=False, default=1)
    regulation_type = Column(String(100))
    authority = Column(String(255))
    description = Column(Text)
    current_status = Column(String(50), default="not_assessed")
    risk_level = Column(String(20), default="medium")
    compliance_deadline = Column(String(20))  # Store as ISO string (YYYY-MM-DD)
    review_frequency = Column(String(50), default="annual")
    responsible_person = Column(String(255))
    evidence_required = Column(Text)  # JSON string of list
    automated_monitoring = Column(Integer, default=0)  # 0/1 for false/true
    documentation_location = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FeatureIdea(Base):
    """Feature ideas (multiple instances)"""
    __tablename__ = 'feature_ideas'

    id = Column(Integer, primary_key=True)
    feature_title = Column(String(255), nullable=False)
    priority_rank = Column(Integer)
    problem_description = Column(Text)
    expected_outcome = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReferenceDocument(Base):
    """Database model for reference documents"""
    __tablename__ = 'reference_documents'

    id = Column(Integer, primary_key=True)
    priority_rank = Column(Integer, nullable=False, default=1)
    file_path = Column(String(512), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)
    upload_date = Column(DateTime, nullable=False, default=func.now())
    file_size = Column(Integer, nullable=False, default=0)
    is_screenshot = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TimeResourceManagement(Base):
    """Time and resource management information (single instance)"""
    __tablename__ = 'time_resource_management'

    id = Column(Integer, primary_key=True)
    primary_activities = Column(Text)
    peak_workload_periods = Column(Text)
    resource_constraints = Column(Text)
    waiting_time = Column(Text)
    overtime_patterns = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TimeAllocation(Base):
    """Time allocations (multiple instances)"""
    __tablename__ = 'time_allocations'

    id = Column(Integer, primary_key=True)
    activity_name = Column(String(255), nullable=False)
    hours_per_week = Column(Integer, nullable=False)
    priority_level = Column(String(50), nullable=False)  # 'High', 'Medium', 'Low'
    pain_point_id = Column(Integer, nullable=True)       # Optional link to pain_points
    process_id = Column(Integer, nullable=True)          # Optional link to processes
    priority_rank = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def initialize_database() -> bool:
    """
    Initialize the SQLite database with SQLAlchemy.

    Returns:
        bool: True if initialization successful, False otherwise
    """
    global engine, SessionLocal

    try:
        # Ensure file structure exists first
        initialize_file_structure()

        db_path = get_database_path()
        _LOGGER.info(f"Initializing database at: {db_path}")

        # Create engine
        engine = create_engine(f"sqlite:///{db_path}", echo=False)

        # Create tables
        Base.metadata.create_all(bind=engine)

        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        _LOGGER.info("Database initialized successfully with SQLAlchemy")
        return True

    except Exception as e:
        _LOGGER.error(f"Failed to initialize database: {e}")
        return False


def database_exists() -> bool:
    """
    Check if the database file exists.

    Returns:
        bool: True if database file exists, False otherwise
    """
    return get_database_path().exists()


def get_database_session() -> Session:
    """
    Get a database session.
    Creates database if it doesn't exist.

    Returns:
        Session: SQLAlchemy database session
    """
    global SessionLocal

    if SessionLocal is None:
        initialize_database()

    return SessionLocal()


def reset_database() -> bool:
    """
    Delete the existing database file and reinitialize.
    USE WITH CAUTION - This will delete all data!

    Returns:
        bool: True if reset successful, False otherwise
    """
    global engine, SessionLocal

    try:
        # Close existing connections
        if engine:
            engine.dispose()

        db_path = get_database_path()

        if db_path.exists():
            db_path.unlink()
            _LOGGER.info(f"Deleted existing database: {db_path}")

        # Reset globals
        engine = None
        SessionLocal = None

        success = initialize_database()
        if success:
            _LOGGER.info("Database reset completed successfully")
        return success

    except Exception as e:
        _LOGGER.error(f"Failed to reset database: {e}")
        return False


def test_database_connection() -> bool:
    """Test database connectivity and basic operations."""
    try:
        session = get_database_session()

        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            'respondent', 'org_map', 'processes', 'pain_points',
            'data_sources', 'compliance', 'compliance_requirements',
            'feature_ideas', 'reference_documents',
            'time_resource_management', 'time_allocations'
        ]

        for table in expected_tables:
            if table not in tables:
                _LOGGER.error(f"Missing table: {table}")
                session.close()
                return False

        session.close()
        _LOGGER.info("Database connection test passed")
        return True

    except Exception as e:
        _LOGGER.error(f"Database connection test failed: {e}")
        return False


# Context manager for database sessions
class DatabaseSession:
    """Context manager for database sessions with automatic cleanup"""

    def __enter__(self) -> Session:
        self.session = get_database_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
