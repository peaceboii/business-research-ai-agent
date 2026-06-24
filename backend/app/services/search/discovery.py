import asyncio
from typing import List
from loguru import logger
from app.services.search.adapters.base import BaseDiscoveryAdapter, RawBusinessCandidate
from app.services.search.adapters.ddg import DuckDuckGoAdapter
from app.services.search.adapters.yahoo import YahooAdapter
from app.services.search.adapters.yelp import YelpAdapter
from app.services.search.adapters.yellowpages import YellowPagesAdapter
from app.services.search.adapters.industry import HealthgradesAdapter, AvvoAdapter, AngiAdapter

class DiscoveryEngine:
    def __init__(self):
        # Register all available adapters
        self.adapters: List[BaseDiscoveryAdapter] = [
            DuckDuckGoAdapter(),
            YahooAdapter(),
            YelpAdapter(),
            YellowPagesAdapter(),
            HealthgradesAdapter(),
            AvvoAdapter(),
            AngiAdapter()
        ]

    async def run_discovery(self, category: str, location: str) -> List[RawBusinessCandidate]:
        """
        Runs discovery concurrently across all registered adapters.
        Catches exceptions per-adapter to ensure failure of one source doesn't block the rest.
        """
        logger.info(f"DiscoveryEngine: Starting discovery for '{category}' in '{location}'")
        
        tasks = []
        for adapter in self.adapters:
            tasks.append(self._safe_discover(adapter, category, location))
            
        results = await asyncio.gather(*tasks)
        
        # Flatten the list of lists
        all_candidates = []
        for i, candidate_list in enumerate(results):
            adapter_name = self.adapters[i].source_name if i < len(self.adapters) else "unknown"
            logger.info(f"DiscoveryEngine: Adapter '{adapter_name}' returned {len(candidate_list)} candidates")
            all_candidates.extend(candidate_list)
            
        logger.info(f"DiscoveryEngine: Discovery complete. Found {len(all_candidates)} raw candidate records.")
        
        # If we have any real (non-simulated) candidates, filter out the simulated ones
        real_candidates = [c for c in all_candidates if not getattr(c, "is_simulated", False)]
        if real_candidates:
            simulated_count = len(all_candidates) - len(real_candidates)
            if simulated_count > 0:
                logger.info(f"DiscoveryEngine: Real candidates found. Filtering out {simulated_count} simulated candidates to prioritize real data.")
            return real_candidates
            
        return all_candidates

    async def _safe_discover(self, adapter: BaseDiscoveryAdapter, category: str, location: str) -> List[RawBusinessCandidate]:
        try:
            # 30s timeout to allow cascading fallbacks (DDG lite -> DDG standard -> Google)
            return await asyncio.wait_for(adapter.discover(category, location), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error(f"DiscoveryEngine: Timeout (30s) reached for adapter '{adapter.source_name}'")
            return []
        except Exception as e:
            logger.error(f"DiscoveryEngine: Error in adapter '{adapter.source_name}': {type(e).__name__}: {e}")
            return []
global_discovery_engine = DiscoveryEngine()

