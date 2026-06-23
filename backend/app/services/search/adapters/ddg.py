import re
from typing import List
from duckduckgo_search import DDGS
from loguru import logger
from app.services.search.adapters.base import BaseDiscoveryAdapter, RawBusinessCandidate
from app.utils.http_utils import get_random_user_agent

class DuckDuckGoAdapter(BaseDiscoveryAdapter):
    @property
    def source_name(self) -> str:
        return "duckduckgo"

    async def discover(self, category: str, location: str) -> List[RawBusinessCandidate]:
        query = f"{category} in {location}"
        logger.info(f"DDGAdapter: Searching for query '{query}'")
        candidates = []

        try:
            # We run DDGS search in an executor or use it directly.
            # We can run it in a threadpool to prevent blocking the async loop.
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            def run_search():
                with DDGS() as ddgs:
                    # Let's search text
                    results = list(ddgs.text(
                        query,
                        max_results=20,
                        backend="html"  # Use html backend for public scraping stability
                    ))
                    return results

            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as pool:
                results = await loop.run_in_executor(pool, run_search)

            for item in results:
                title = item.get("title", "")
                url = item.get("href", "")
                body = item.get("body", "")

                # Exclude common aggregator/directory sites so we find direct business sites here,
                # because directories are searched separately.
                if any(domain in url.lower() for domain in ["yelp.com", "yellowpages.com", "healthgrades.com", "avvo.com", "facebook.com", "linkedin.com", "tripadvisor.com", "foursquare.com", "wikipedia.org"]):
                    continue

                # Parse phone number from body if available
                phone = None
                phone_match = re.search(r'\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', body)
                if phone_match:
                    phone = phone_match.group(0).strip()

                # Parse address (basic attempt: look for zip codes and state abbreviations in USA context)
                address = None
                address_match = re.search(r'\b\d+\s+[A-Za-z0-9\s,\.]+,\s*[A-Z]{2}\s+\d{5}\b', body)
                if address_match:
                    address = address_match.group(0).strip()

                # Clean name: remove website extensions or common titles
                clean_name = title
                # Remove suffix like " | Company Name" or "- Austin, TX"
                clean_name = re.split(r' \| | - |: ', clean_name)[0].strip()

                candidates.append(RawBusinessCandidate(
                    name=clean_name,
                    website=url,
                    address=address,
                    phone=phone,
                    source_name=self.source_name,
                    source_url=url,
                ))
            
            logger.info(f"DDGAdapter: Discovered {len(candidates)} candidates.")

        except Exception as e:
            logger.error(f"DDGAdapter error during discovery: {e}")
            # Do not fail completely; return empty list as fallback.
            
        return candidates
