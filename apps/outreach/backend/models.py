"""
Aethermoor Outreach -- SQLAlchemy models.
Civic and business workflow tracking for Port Angeles, WA.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    location = Column(String(100), nullable=False)
    intent = Column(Text, nullable=False)
    intent_classified = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    cases = relationship("Case", back_populates="project", cascade="all, delete-orphan")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    status = Column(String(50), default="open")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="cases")
    workflow_steps = relationship("WorkflowStep", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="case", cascade="all, delete-orphan")
    events = relationship("CaseEvent", back_populates="case", cascade="all, delete-orphan")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    agency = Column(String(200), nullable=True)
    estimated_time = Column(String(100), nullable=True)
    required_docs = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    completed_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="workflow_steps")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    doc_type = Column(String(100), nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    case = relationship("Case", back_populates="documents")


class RoutingTarget(Base):
    __tablename__ = "routing_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    agency = Column(String(200), nullable=False)
    contact_info = Column(String(300), nullable=True)
    phone = Column(String(50), nullable=True)
    hours = Column(String(100), nullable=True)
    website = Column(String(300), nullable=True)
    notes = Column(Text, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    routing_target_id = Column(Integer, ForeignKey("routing_targets.id"), nullable=True)
    to_email = Column(String(300), nullable=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String(50), default="draft")
    sent_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="messages")
    routing_target = relationship("RoutingTarget")


class CaseEvent(Base):
    __tablename__ = "case_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    case = relationship("Case", back_populates="events")


def get_engine(db_path: str = "outreach.db"):
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(db_path: str = "outreach.db"):
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(db_path: str = "outreach.db"):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
