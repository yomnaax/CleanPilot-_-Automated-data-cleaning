"""
ORM models for AutoClean.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Float,
    Boolean,
    Text,
    ForeignKey,
    Enum,
    JSON,
)
from sqlalchemy.orm import relationship

from .base import Base


class DatasetPurpose(str, enum.Enum):
    RULE_EXTRACTION = "rule_extraction"
    CLEANING = "cleaning"


class Modality(str, enum.Enum):
    TABULAR = "tabular"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"


class Domain(str, enum.Enum):
    GENERAL = "general"  # Default, works for any data
    ECOMMERCE = "ecommerce"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    RETAIL = "retail"
    EDUCATION = "education"
    HR = "hr" 


class RuleSource(str, enum.Enum):
    EXTRACTED = "extracted"
    RAG = "rag"
    USER = "user"


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    purpose = Column(Enum(DatasetPurpose), nullable=False)
    modality = Column(Enum(Modality), nullable=False)
    domain = Column(Enum(Domain), nullable=True, default=Domain.GENERAL) 
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)  # Renamed from 'metadata' (reserved in SQLAlchemy)
    column_mappings = Column(JSON, nullable=True)  # Maps dataset columns to canonical concepts

    rules = relationship("Rule", back_populates="dataset")
    runs = relationship("Run", back_populates="dataset")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    source = Column(Enum(RuleSource), nullable=False)
    modality = Column(Enum(Modality), nullable=False)
    targets = Column(JSON, nullable=True)  # columns/fields affected
    predicate = Column(Text, nullable=False)  # machine-readable rule
    action = Column(Text, nullable=True)  # cleaning action
    confidence = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    approved = Column(Boolean, nullable=True, default=None)  # User approval status: None=pending, True=approved, False=rejected

    dataset = relationship("Dataset", back_populates="rules")
    feedback = relationship("Feedback", back_populates="rule")


class RunType(str, enum.Enum):
    # Dataset profiling (statistics, schema inference)
    PROFILING = "profiling"
    RULE_EXTRACTION = "rule_extraction"
    CLEANING = "cleaning"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    run_type = Column(Enum(RunType), nullable=False)
    status = Column(Enum(RunStatus), default=RunStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    summary = Column(JSON, nullable=True)

    dataset = relationship("Dataset", back_populates="runs")


class FeedbackDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=False)
    decision = Column(Enum(FeedbackDecision), nullable=False)
    comment = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)  # optional structured edits
    created_at = Column(DateTime, default=datetime.utcnow)

    rule = relationship("Rule", back_populates="feedback")


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String, unique=True, index=True, nullable=False)
    full_name        = Column(String, nullable=True)
    hashed_password  = Column(String, nullable=False)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)