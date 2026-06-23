import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from typing import List
from loguru import logger
from app.services.search.adapters.base import BaseDiscoveryAdapter, RawBusinessCandidate

class DuckDuckGoAdapter(BaseDiscoveryAdapter):
    @property
    def source_name(self) -> str:
        return "duckduckgo"

    async def discover(self, category: str, location: str) -> List[RawBusinessCandidate]:
        query = f"{category} in {location}"
        logger.info(f"DDGAdapter: Custom scraping query '{query}'")
        candidates = []

        try:
            import asyncio
            
            def run_search():
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
                req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=10.0) as response:
                    html = response.read()
                    soup = BeautifulSoup(html, "html.parser")
                    return soup.find_all("div", class_="result__body")

            loop = asyncio.get_running_loop()
            result_elements = await loop.run_in_executor(None, run_search)
            logger.info(f"DDGAdapter: Raw HTML fetch yielded {len(result_elements)} elements.")

            for r in result_elements:
                title_el = r.find("a", class_="result__url")
                snippet_el = r.find("a", class_="result__snippet")
                
                if not title_el:
                    continue
                    
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                
                # Parse final destination URL from DuckDuckGo redirect link
                try:
                    parsed_url = urllib.parse.urlparse(link)
                    qs = urllib.parse.parse_qs(parsed_url.query)
                    final_url = qs.get("uddg", [link])[0]
                except Exception:
                    final_url = link

                # Exclude directories
                if any(domain in final_url.lower() for domain in ["yelp.com", "yellowpages.com", "healthgrades.com", "avvo.com", "facebook.com", "linkedin.com", "tripadvisor.com", "foursquare.com", "wikipedia.org"]):
                    continue

                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                # Parse phone number from snippet
                phone = None
                phone_match = re.search(r'\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', snippet)
                if phone_match:
                    phone = phone_match.group(0).strip()

                # Parse address from snippet
                address = None
                address_match = re.search(r'\b\d+\s+[A-Za-z0-9\s,\.]+,\s*[A-Z]{2}\s+\d{5}\b', snippet)
                if address_match:
                    address = address_match.group(0).strip()

                # Clean name: remove website suffixes
                clean_name = title
                clean_name = re.split(r' \| | - |: ', clean_name)[0].strip()

                candidates.append(RawBusinessCandidate(
                    name=clean_name,
                    website=final_url,
                    address=address,
                    phone=phone,
                    source_name=self.source_name,
                    source_url=final_url,
                ))
            
            logger.info(f"DDGAdapter: Discovered {len(candidates)} real candidates.")

        except Exception as e:
            logger.error(f"DDGAdapter error during custom discovery: {e}")
            
        return candidates

