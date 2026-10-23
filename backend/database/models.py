"""
SQLAlchemy ORM models — one class per database table.
Tables are created automatically on startup via Base.metadata.create_all().
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from database.db import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HeatRiskReport(Base):
    __tablename__ = "heat_risk_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    temperature = Column(Float)       # °C
    humidity = Column(Float)          # %
    risk_score = Column(Float)        # 0–10
    risk_level = Column(String)       # Low / Moderate / High / Extreme
    gemini_summary = Column(Text)     # AI-generated advice
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class ShadeAnalysis(Base):
    __tablename__ = "shade_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    image_filename = Column(String)
    shade_percent = Column(Float)     # % shade detected by OpenCV
    ai_description = Column(Text)     # Gemini Vision description
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())


class BudgetPlan(Base):
    __tablename__ = "budget_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    total_budget = Column(Float)      # ₹
    interventions = Column(Text)      # JSON string
    expected_savings = Column(Text)   # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HealthProfile(Base):
    """
    Anonymous health profile for personalised heat-safety guidance.

    Privacy design:
    - Identified only by a random UUID session_id (no name, email, or device ID).
    - consent_given must be True before any record is created.
    - age_group stores a broad band (e.g. "18-40") — never exact age.
    - conditions stores a comma-separated list of pre-defined category labels only
      (never free-text clinical notes).
    - Outdoor worker flag adds relevant occupational advice.
    """
    __tablename__ = "health_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False, index=True)  # random UUID
    consent_given = Column(Boolean, nullable=False, default=False)
    age_group = Column(String, nullable=True)      # "under-18" | "18-40" | "41-60" | "60+"
    conditions = Column(String, nullable=True)      # comma-separated category labels
    outdoor_worker = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
