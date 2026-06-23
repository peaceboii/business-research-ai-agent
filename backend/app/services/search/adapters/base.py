from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RawBusinessCandidate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source_name: str
    source_url: Optional[str] = None
    working_hours: Optional[Dict[str, Any]] = None
    services: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    social_profiles: List[str] = Field(default_factory=list)

class BaseDiscoveryAdapter(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier of the discovery source."""
        pass

    @abstractmethod
    async def discover(self, category: str, location: str) -> List[RawBusinessCandidate]:
        """
        Search for business candidates based on category and location.
        Should handle rate limits, rotating user agents, and errors gracefully.
        """
        pass
