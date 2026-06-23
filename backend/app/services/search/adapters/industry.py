import random
from typing import List
from loguru import logger
from app.services.search.adapters.base import BaseDiscoveryAdapter, RawBusinessCandidate
from faker import Faker

class HealthgradesAdapter(BaseDiscoveryAdapter):
    @property
    def source_name(self) -> str:
        return "healthgrades"

    async def discover(self, category: str, location: str) -> List[RawBusinessCandidate]:
        # Do not generate mock data to prevent hallucinations.
        # Real medical providers will be found via DuckDuckGo web search adapter.
        return []


class AvvoAdapter(BaseDiscoveryAdapter):
    @property
    def source_name(self) -> str:
        return "avvo"

    async def discover(self, category: str, location: str) -> List[RawBusinessCandidate]:
        # Do not generate mock data to prevent hallucinations.
        # Real legal providers will be found via DuckDuckGo web search adapter.
        return []


class AngiAdapter(BaseDiscoveryAdapter):
    @property
    def source_name(self) -> str:
        return "angi"

    async def discover(self, category: str, location: str) -> List[RawBusinessCandidate]:
        # Do not generate mock data to prevent hallucinations.
        # Real contractors will be found via DuckDuckGo web search adapter.
        return []
