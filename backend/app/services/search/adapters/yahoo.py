import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from typing import List
from loguru import logger
from app.services.search.adapters.base import BaseDiscoveryAdapter, RawBusinessCandidate

class YahooAdapter(BaseDiscoveryAdapter):
    @property
    def source_name(self) -> str:
        return "yahoo"

    async def discover(self, category: str, location: str) -> List[RawBusinessCandidate]:
        query = f"{category} in {location}"
        logger.info(f"YahooAdapter: Searching Yahoo for query '{query}'")
        candidates = []

        try:
            import asyncio
            
            def run_search_workflow():
                url = f"https://search.yahoo.com/search?p={urllib.parse.quote_plus(query)}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                req = urllib.request.Request(url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=10.0) as response:
                        html = response.read()
                        soup = BeautifulSoup(html, "html.parser")
                        return soup.find_all("div", class_="algo")
                except Exception as e:
                    logger.error(f"YahooAdapter: Page fetch failed: {e}")
                    return []

            loop = asyncio.get_running_loop()
            result_elements = await loop.run_in_executor(None, run_search_workflow)
            logger.info(f"YahooAdapter: Raw HTML fetch yielded {len(result_elements)} total elements.")

            for r in result_elements:
                title_div = r.find("div", class_="compTitle")
                if not title_div:
                    continue
                a = title_div.find("a")
                if not a:
                    continue

                raw_link = a.get("href", "")
                clean_link = raw_link
                if "RU=" in raw_link:
                    try:
                        match = re.search(r'RU=([^/&]+)', raw_link)
                        if match:
                            clean_link = urllib.parse.unquote(match.group(1))
                    except Exception:
                        pass

                h3 = title_div.find("h3")
                title_text = h3.get_text(strip=True) if h3 else a.get_text(strip=True)

                snippet_div = r.find("div", class_="compText") or r.find("span", class_="fc-2nd")
                snippet = snippet_div.get_text(strip=True) if snippet_div else ""

                # Exclude directories list pages
                directory_domains = [
                    "yelp.com/c/", "yelp.com/search",
                    "yellowpages.com/search", "yellowpages.com/state",
                    "healthgrades.com/use-search", "avvo.com/search", 
                    "tripadvisor.com/Search", "foursquare.com/explore", 
                    "wikipedia.org", "crunchbase.com/organization", "zoominfo.com/c/", 
                    "glassdoor.com", "mapquest.com", "yahoo.com", "local.com/search", 
                    "find-us-here.com", "dialindia.com", "bharatbiz.com", 
                    "exportersindia.com", "tradeindia.com"
                ]
                
                is_directory_list = False
                for domain in directory_domains:
                    if domain in clean_link.lower():
                        is_directory_list = True
                        break
                
                if "justdial.com" in clean_link.lower() and "/nct-" in clean_link.lower():
                    is_directory_list = True
                if "sulekha.com" in clean_link.lower() and "/all-" in clean_link.lower():
                    is_directory_list = True
                if "indiamart.com" in clean_link.lower() and ("/dir/" in clean_link.lower() or "search.mp" in clean_link.lower()):
                    is_directory_list = True

                if is_directory_list:
                    continue

                # Parse phone number from snippet
                phone = None
                phone_match = re.search(
                    r'(?:\+?91|0)?[-\s]?[6-9]\d{4}[-\s]?\d{5}'
                    r'|'
                    r'(?:\+?91|0)?[-\s]?\d{2,5}[-\s]?\d{6,8}'
                    r'|'
                    r'\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
                    r'|'
                    r'\+?[0-9]{1,4}[-.\s]?\(?[0-9]{2,5}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,6}',
                    snippet
                )
                if phone_match:
                    phone = phone_match.group(0).strip()

                # Parse address from snippet
                address = None
                address_match = re.search(r'\b\d+\s+[A-Za-z0-9\s,\.]+,\s*[A-Z]{2}\s+\d{5}\b', snippet)
                if address_match:
                    address = address_match.group(0).strip()
                else:
                    general_match = re.search(
                        r'\b\d*[A-Za-z0-9\s,\.]+(?:Road|Rd|Street|St|Nagar|Puram|Complex|Bldg|Building|Floor|Block|Colony|Plaza|Sector|Zone)[A-Za-z0-9\s,\.]+\b\d{5,6}\b',
                        snippet,
                        re.IGNORECASE
                    )
                    if general_match:
                        address = general_match.group(0).strip()

                clean_name = title_text
                clean_name = re.split(r' \| | - |: ', clean_name)[0].strip()

                candidates.append(RawBusinessCandidate(
                    name=clean_name,
                    website=clean_link,
                    address=address,
                    phone=phone,
                    source_name=self.source_name,
                    source_url=clean_link,
                ))

            logger.info(f"YahooAdapter: Discovered {len(candidates)} candidates.")

        except Exception as e:
            logger.error(f"YahooAdapter error: {e}")

        return candidates
