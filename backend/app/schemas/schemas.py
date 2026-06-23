from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class QueryBase(BaseModel):
    query_text: str
    category: Optional[str] = None
    location: Optional[str] = None

class QueryCreate(QueryBase):
    pass

class QueryResponse(QueryBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BusinessBase(BaseModel):
    business_name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    working_hours: Optional[Dict[str, Any]] = Field(default_factory=dict)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    services: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    license_information: Optional[str] = None
    certifications: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    social_profiles: List[str] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list)
    source_urls: Dict[str, List[str]] = Field(default_factory=dict)
    verification_score: float = 0.0

class BusinessCreate(BusinessBase):
    query_id: Optional[int] = None

class BusinessResponse(BusinessBase):
    id: int
    query_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BusinessSourceResponse(BaseModel):
    id: int
    business_id: int
    source_name: str
    url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    working_hours: Optional[Dict[str, Any]] = None
    certifications: List[str] = []
    awards: List[str] = []
    services: List[str] = []
    specialties: List[str] = []
    retrieved_at: datetime

    class Config:
        from_attributes = True

class ConflictResponse(BaseModel):
    id: int
    business_id: int
    field_name: str
    conflicting_values: List[str]
    resolved: bool
    resolved_value: Optional[str] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ConflictResolveRequest(BaseModel):
    resolved_value: str

class ResearchReportResponse(BaseModel):
    id: int
    query_id: int
    duration: float
    total_discovered: int
    total_verified: int
    duplicates_removed: int
    sources_used: int
    website_coverage: float
    phone_coverage: float
    hours_coverage: float
    report_markdown: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AnalyticsResponse(BaseModel):
    records_with_phone: int
    records_with_website: int
    records_with_hours: int
    records_with_license: int
    total_records: int
    phone_coverage_pct: float
    website_coverage_pct: float
    hours_coverage_pct: float
    license_coverage_pct: float

class StatsResponse(BaseModel):
    total_queries: int
    total_businesses: int
    total_reports: int
    duplicates_removed_total: int
    avg_duration: float
    recent_activity: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    status: str
    redis_connected: bool
    db_connected: bool
    timestamp: datetime

class ResearchRequest(BaseModel):
    query: str
