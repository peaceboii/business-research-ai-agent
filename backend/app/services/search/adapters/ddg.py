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
            import time
            
            def run_search_workflow():
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Origin": "https://html.duckduckgo.com",
                    "Referer": "https://html.duckduckgo.com/"
                }
                
                # Fetch Page 1 (GET)
                url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
                req = urllib.request.Request(url, headers=headers)
                
                all_results = []
                try:
                    with urllib.request.urlopen(req, timeout=10.0) as response:
                        html = response.read()
                        soup = BeautifulSoup(html, "html.parser")
                        all_results.extend(soup.find_all("div", class_="result__body"))
                except Exception as e:
                    logger.error(f"DDGAdapter: Page 1 fetch failed: {e}")
                    return []

                # Find next page pagination form to fetch Page 2
                nav_form = None
                for form in soup.find_all("form", action="/html/"):
                    if form.find("input", attrs={"name": "s"}):
                        nav_form = form
                        break

                if nav_form:
                    inputs = nav_form.find_all("input")
                    post_data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name")}
                    offset = post_data.get("s", "0")
                    if offset != "0":
                        time.sleep(1.0) # Be polite
                        try:
                            post_url = "https://html.duckduckgo.com/html/"
                            data_bytes = urllib.parse.urlencode(post_data).encode("utf-8")
                            req2 = urllib.request.Request(post_url, data=data_bytes, headers=headers)
                            with urllib.request.urlopen(req2, timeout=10.0) as response2:
                                html2 = response2.read()
                                soup2 = BeautifulSoup(html2, "html.parser")
                                all_results.extend(soup2.find_all("div", class_="result__body"))
                        except Exception as e:
                            logger.error(f"DDGAdapter: Page 2 fetch failed: {e}")
                
                return all_results

            loop = asyncio.get_running_loop()
            result_elements = await loop.run_in_executor(None, run_search_workflow)
            logger.info(f"DDGAdapter: Raw HTML fetch yielded {len(result_elements)} total elements.")

            for r in result_elements:
                title_el = r.find("a", class_="result__a") or r.find("a", class_="result__url")
                snippet_el = r.find("a", class_="result__snippet")
                
                if not title_el:
                    continue
                    
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                
                # Exclude raw advertisement redirects
                if "duckduckgo.com/y.js" in link.lower() or "/y.js" in link.lower():
                    continue

                # Parse final destination URL from DuckDuckGo redirect link
                try:
                    parsed_url = urllib.parse.urlparse(link)
                    qs = urllib.parse.parse_qs(parsed_url.query)
                    final_url = qs.get("uddg", [link])[0]
                except Exception:
                    final_url = link

                if "duckduckgo.com/y.js" in final_url.lower() or "/y.js" in final_url.lower():
                    continue

                # Exclude directories list pages (we allow facebook, linkedin, and specific detail pages)
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
                    if domain in final_url.lower():
                        is_directory_list = True
                        break
                
                # Smart directory filtering for list indices
                if "justdial.com" in final_url.lower() and "/nct-" in final_url.lower():
                    is_directory_list = True
                if "sulekha.com" in final_url.lower() and "/all-" in final_url.lower():
                    is_directory_list = True
                if "indiamart.com" in final_url.lower() and ("/dir/" in final_url.lower() or "search.mp" in final_url.lower()):
                    is_directory_list = True

                if is_directory_list:
                    continue

                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                # Parse phone number from snippet (supports US, Indian, and general international formats)
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
                    # General address pattern with street suffix and zip/postal code
                    general_match = re.search(
                        r'\b\d*[A-Za-z0-9\s,\.]+(?:Road|Rd|Street|St|Nagar|Puram|Complex|Bldg|Building|Floor|Block|Colony|Plaza|Sector|Zone)[A-Za-z0-9\s,\.]+\b\d{5,6}\b',
                        snippet,
                        re.IGNORECASE
                    )
                    if general_match:
                        address = general_match.group(0).strip()

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

