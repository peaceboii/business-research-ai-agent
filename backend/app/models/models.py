import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(String, index=True, nullable=False)
    category = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    reports = relationship("ResearchReport", back_populates="query", cascade="all, delete-orphan")


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=True)
    business_name = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    working_hours = Column(JSON, nullable=True)  # dict or list of hours
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    services = Column(JSON, default=list)  # list[str]
    specialties = Column(JSON, default=list)  # list[str]
    license_information = Column(String, nullable=True)
    certifications = Column(JSON, default=list)  # list[str]
    awards = Column(JSON, default=list)  # list[str]
    social_profiles = Column(JSON, default=list)  # list[str]
    image_urls = Column(JSON, default=list)  # list[str]
    source_urls = Column(JSON, default=dict)  # dict of {field_name: list_of_sources}
    verification_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sources = relationship("BusinessSource", back_populates="business", cascade="all, delete-orphan")
    verification_logs = relationship("VerificationLog", back_populates="business", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="business", cascade="all, delete-orphan")


class BusinessSource(Base):
    __tablename__ = "business_sources"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    source_name = Column(String, nullable=False)  # e.g., yelp, ddg, yellowpages
    url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    working_hours = Column(JSON, nullable=True)
    certifications = Column(JSON, default=list)
    awards = Column(JSON, default=list)
    services = Column(JSON, default=list)
    specialties = Column(JSON, default=list)
    retrieved_at = Column(DateTime, default=datetime.datetime.utcnow)

    business = relationship("Business", back_populates="sources")


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    field_name = Column(String, nullable=False)  # phone, address, website, email, etc.
    source = Column(String, nullable=False)
    value = Column(String, nullable=True)
    is_valid = Column(Boolean, default=True)
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)

    business = relationship("Business", back_populates="verification_logs")


class Conflict(Base):
    __tablename__ = "conflicts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    field_name = Column(String, nullable=False)  # e.g. phone
    conflicting_values = Column(JSON, nullable=False)  # list of [value1, value2]
    resolved = Column(Boolean, default=False)
    resolved_value = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="conflicts")


class CacheStat(Base):
    __tablename__ = "cache_stats"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    hit_count = Column(Integer, default=0)
    miss_count = Column(Integer, default=0)
    last_queried = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    duration = Column(Float, nullable=False)  # in seconds
    total_discovered = Column(Integer, default=0)
    total_verified = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    sources_used = Column(Integer, default=0)
    website_coverage = Column(Float, default=0.0)  # percentage
    phone_coverage = Column(Float, default=0.0)  # percentage
    hours_coverage = Column(Float, default=0.0)  # percentage
    report_markdown = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    query = relationship("Query", back_populates="reports")
