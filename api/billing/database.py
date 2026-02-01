"""
Database models for SCBE billing system.

Uses SQLAlchemy with SQLite for MVP (easily upgradeable to PostgreSQL).
"""

import os
import uuid
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Float,
    Text,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scbe_billing.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Customer(Base):
    """Customer record, maps to Stripe Customer."""

    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="customer")
    api_keys = relationship("ApiKey", back_populates="customer")
    usage_records = relationship("UsageRecord", back_populates="customer")


class Subscription(Base):
    """Subscription record, maps to Stripe Subscription."""

    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    stripe_price_id = Column(String(255), nullable=True)
    tier = Column(
        String(20),
        CheckConstraint("tier IN ('FREE', 'STARTER', 'PRO', 'ENTERPRISE')"),
        nullable=False,
        default="FREE",
    )
    status = Column(
        String(20),
        CheckConstraint("status IN ('active', 'past_due', 'canceled', 'trialing', 'paused')"),
        nullable=False,
        default="active",
    )
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="subscriptions")

    __table_args__ = (Index("idx_subscriptions_customer", "customer_id"),)


class ApiKey(Base):
    """API key record for customer authentication."""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    key_hash = Column(String(64), nullable=False)  # SHA-256 hash
    key_prefix = Column(String(12), nullable=False)  # First 8 chars for display
    name = Column(String(100), default="Default")
    permissions = Column(String(50), default="full")
    rate_limit_override = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_hash", "key_hash"),
        Index("idx_api_keys_customer", "customer_id"),
    )


class UsageRecord(Base):
    """Usage record for metering API calls."""

    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    api_key_id = Column(String(36), ForeignKey("api_keys.id"), nullable=False)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    response_status = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    request_size_bytes = Column(Integer, nullable=True)
    response_size_bytes = Column(Integer, nullable=True)
    decision = Column(String(20), nullable=True)  # ALLOW/DENY/QUARANTINE
    billing_period = Column(String(7), nullable=False)  # YYYY-MM

    # Relationships
    customer = relationship("Customer", back_populates="usage_records")

    __table_args__ = (
        Index("idx_usage_customer_period", "customer_id", "billing_period"),
        Index("idx_usage_timestamp", "timestamp"),
    )


class UsageAggregate(Base):
    """Aggregated usage for performance (hourly/daily/monthly rollups)."""

    __tablename__ = "usage_aggregates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    period_type = Column(
        String(10),
        CheckConstraint("period_type IN ('hourly', 'daily', 'monthly')"),
        nullable=False,
    )
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_requests = Column(Integer, default=0)
    authorize_requests = Column(Integer, default=0)
    govern_requests = Column(Integer, default=0)
    allow_count = Column(Integer, default=0)
    deny_count = Column(Integer, default=0)
    quarantine_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, nullable=True)


class BillingEvent(Base):
    """Billing events for invoice history."""

    __tablename__ = "billing_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    stripe_event_id = Column(String(255), unique=True, nullable=True)
    event_type = Column(String(50), nullable=False)
    amount_cents = Column(Integer, nullable=True)
    currency = Column(String(3), default="usd")
    invoice_url = Column(Text, nullable=True)
    invoice_pdf = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(Text, nullable=True)  # JSON


def init_db():
    """Initialize the database, creating all tables."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_db() -> Session:
    """Get a database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a database session (for FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
