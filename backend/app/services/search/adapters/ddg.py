import re
import urllib.request
import urllib.parse
import json
from bs4 import BeautifulSoup
from typing import List
from loguru import logger
from app.services.search.adapters.base import BaseDiscoveryAdapter, RawBusinessCandidate
from app.utils.extraction_utils import extract_phone_from_text, extract_address_from_text

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
                # Rotate through multiple User-Agent strings to avoid detection
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
                ]
                import random
                ua = random.choice(user_agents)
                
                headers = {
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "identity",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
                
                # Try DuckDuckGo HTML lite endpoint (more reliable from cloud servers)
                url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote_plus(query)}"
                logger.info(f"DDGAdapter: Fetching lite endpoint: {url}")
                req = urllib.request.Request(url, headers=headers)
                
                all_results = []
                try:
                    with urllib.request.urlopen(req, timeout=12.0) as response:
                        html = response.read()
                        logger.info(f"DDGAdapter: Got response, status={response.status}, length={len(html)} bytes")
                        soup = BeautifulSoup(html, "html.parser")
                        
                        # Lite version uses table rows for results
                        # Each result has a link in a <a> tag with class 'result-link'
                        result_links = soup.find_all("a", class_="result-link")
                        if result_links:
                            logger.info(f"DDGAdapter: Found {len(result_links)} result-link elements (lite)")
                            for link in result_links:
                                all_results.append(("lite", link))
                        else:
                            # Fallback: try standard HTML version
                            logger.info("DDGAdapter: No lite results, trying standard HTML endpoint...")
                            url2 = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
                            headers2 = dict(headers)
                            headers2["Origin"] = "https://html.duckduckgo.com"
                            headers2["Referer"] = "https://html.duckduckgo.com/"
                            req2 = urllib.request.Request(url2, headers=headers2)
                            
                            with urllib.request.urlopen(req2, timeout=12.0) as response2:
                                html2 = response2.read()
                                logger.info(f"DDGAdapter: Standard HTML response length={len(html2)} bytes")
                                soup2 = BeautifulSoup(html2, "html.parser")
                                body_elements = soup2.find_all("div", class_="result__body")
                                logger.info(f"DDGAdapter: Found {len(body_elements)} result__body elements (standard)")
                                for elem in body_elements:
                                    all_results.append(("standard", elem))
                                    
                except Exception as e:
                    logger.error(f"DDGAdapter: Fetch failed: {type(e).__name__}: {e}")
                    
                    # Last resort fallback: try Google search scraping
                    try:
                        logger.info("DDGAdapter: Trying Google search fallback...")
                        google_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&num=20"
                        google_headers = {
                            "User-Agent": ua,
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                            "Accept-Language": "en-US,en;q=0.5",
                        }
                        google_req = urllib.request.Request(google_url, headers=google_headers)
                        with urllib.request.urlopen(google_req, timeout=12.0) as google_resp:
                            google_html = google_resp.read()
                            logger.info(f"DDGAdapter: Google response length={len(google_html)} bytes")
                            google_soup = BeautifulSoup(google_html, "html.parser")
                            # Google results are in <div class="g"> elements
                            for g in google_soup.find_all("div", class_="g"):
                                all_results.append(("google", g))
                    except Exception as ge:
                        logger.error(f"DDGAdapter: Google fallback also failed: {type(ge).__name__}: {ge}")
                    
                return all_results

            loop = asyncio.get_running_loop()
            result_elements = await loop.run_in_executor(None, run_search_workflow)
            logger.info(f"DDGAdapter: Total elements to parse: {len(result_elements)}")

            for result_type, r in result_elements:
                try:
                    title = ""
                    link = ""
                    snippet = ""
                    
                    if result_type == "lite":
                        # Lite version: <a class="result-link"> contains the URL and text
                        title = r.get_text(strip=True)
                        link = r.get("href", "")
                        # Get snippet from next sibling or parent
                        parent_td = r.find_parent("td")
                        if parent_td:
                            snippet_td = parent_td.find_next_sibling("td")
                            if snippet_td:
                                snippet = snippet_td.get_text(strip=True)
                    elif result_type == "standard":
                        title_el = r.find("a", class_="result__a") or r.find("a", class_="result__url")
                        snippet_el = r.find("a", class_="result__snippet")
                        if not title_el:
                            continue
                        title = title_el.get_text(strip=True)
                        link = title_el.get("href", "")
                        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    elif result_type == "google":
                        # Google result parsing
                        a_tag = r.find("a")
                        if not a_tag:
                            continue
                        h3 = r.find("h3")
                        title = h3.get_text(strip=True) if h3 else a_tag.get_text(strip=True)
                        link = a_tag.get("href", "")
                        # Clean Google redirect URLs
                        if link.startswith("/url?"):
                            try:
                                parsed = urllib.parse.urlparse(link)
                                qs = urllib.parse.parse_qs(parsed.query)
                                link = qs.get("q", [link])[0]
                            except Exception:
                                pass
                        # Snippet
                        snippet_div = r.find("div", class_="VwiC3b") or r.find("span", class_="aCOpRe")
                        snippet = snippet_div.get_text(strip=True) if snippet_div else ""
                    
                    if not title or not link:
                        continue
                    
                    # Exclude DuckDuckGo ad redirects    
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

                    # Exclude directories list pages
                    directory_domains = [
                        "yelp.com/c/", "yelp.com/search",
                        "yellowpages.com/search", "yellowpages.com/state",
                        "healthgrades.com/use-search", "avvo.com/search", 
                        "tripadvisor.com/Search", "foursquare.com/explore", 
                        "wikipedia.org", "crunchbase.com/organization", "zoominfo.com/c/", 
                        "glassdoor.com", "mapquest.com", "yahoo.com", "local.com/search", 
                        "find-us-here.com", "dialindia.com", "bharatbiz.com", 
                        "exportersindia.com", "tradeindia.com",
                        "google.com/search", "google.com/maps",
                    ]
                    
                    is_directory_list = False
                    for domain in directory_domains:
                        if domain in final_url.lower():
                            is_directory_list = True
                            break
                    
                    if "justdial.com" in final_url.lower() and "/nct-" in final_url.lower():
                        is_directory_list = True
                    if "sulekha.com" in final_url.lower() and "/all-" in final_url.lower():
                        is_directory_list = True
                    if "indiamart.com" in final_url.lower() and ("/dir/" in final_url.lower() or "search.mp" in final_url.lower()):
                        is_directory_list = True

                    if is_directory_list:
                        continue

                    # Parse phone number and address from snippet
                    phone = extract_phone_from_text(snippet)
                    address = extract_address_from_text(snippet)

                    # Clean name: remove website suffixes
                    clean_name = title
                    clean_name = re.split(r' \| | - |: ', clean_name)[0].strip()
                    
                    if clean_name and len(clean_name) > 2:
                        candidates.append(RawBusinessCandidate(
                            name=clean_name,
                            website=final_url,
                            address=address,
                            phone=phone,
                            source_name=self.source_name,
                            source_url=final_url,
                        ))
                except Exception as parse_err:
                    logger.warning(f"DDGAdapter: Failed to parse result element: {parse_err}")
                    continue
            
            logger.info(f"DDGAdapter: Discovered {len(candidates)} real candidates.")

        except Exception as e:
            logger.error(f"DDGAdapter error during custom discovery: {e}")
            
        return candidates
