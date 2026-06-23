import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from loguru import logger
from app.services.search.adapters.base import BaseDiscoveryAdapter, RawBusinessCandidate
from app.utils.http_utils import http_get_with_retry

class YellowPagesAdapter(BaseDiscoveryAdapter):
    @property
    def source_name(self) -> str:
        return "yellowpages"

    async def discover(self, category: str, location: str) -> List[RawBusinessCandidate]:
        safe_category = urllib.parse.quote_plus(category)
        safe_location = urllib.parse.quote_plus(location)
        url = f"https://www.yellowpages.com/search?search_terms={safe_category}&geo_location_terms={safe_location}"
        
        logger.info(f"YellowPagesAdapter: Searching YellowPages: {url}")
        candidates = []

        try:
            response = await http_get_with_retry(url, check_robots=True)
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # YellowPages lists businesses inside divs with class 'result' or 'info'
                listings = soup.find_all("div", class_="info")
                
                for item in listings:
                    name_tag = item.find("a", class_="business-name")
                    if not name_tag:
                        continue
                    name = name_tag.get_text(strip=True)
                    yp_url = f"https://www.yellowpages.com{name_tag.get('href', '')}" if name_tag.get("href", "").startswith("/") else name_tag.get("href", "")
                    
                    # Phone
                    phone_tag = item.find("div", class_="phones") or item.find("div", class_="phone")
                    phone = phone_tag.get_text(strip=True) if phone_tag else None
                    
                    # Address
                    adr_tag = item.find("div", class_="adr") or item.find("p", class_="adr")
                    address = adr_tag.get_text(strip=True) if adr_tag else None
                    
                    # Website
                    web_tag = item.find("a", class_="track-visit-website")
                    website = web_tag.get("href") if web_tag else None
                    
                    candidates.append(RawBusinessCandidate(
                        name=name,
                        address=address,
                        phone=phone,
                        website=website,
                        source_name=self.source_name,
                        source_url=yp_url
                    ))
            
            # Return empty if no candidates found
            if not candidates:
                logger.info("YellowPagesAdapter: Empty results or blocked. Returning empty list.")
                candidates = []

        except Exception as e:
            logger.error(f"YellowPagesAdapter error: {e}. Returning empty list.")
            candidates = []

        return candidates

    def _simulate_discovery(self, category: str, location: str) -> List[RawBusinessCandidate]:
        """
        Simulate Yellow Pages directory items.
        """
        import random
        from faker import Faker
        fake = Faker()
        
        cat_title = category.title()
        loc_title = location.title()
        
        candidates = []
        count = random.randint(3, 7)
        for i in range(count):
            name = f"{loc_title} {cat_title} Services"
            if i == 1:
                name = f"{fake.last_name()} & Co. {cat_title}"
            elif i == 2:
                name = f"{fake.first_name()}'s {cat_title}"
                
            area_code = random.randint(200, 999)
            prefix = random.randint(200, 999)
            line = random.randint(1000, 9999)
            phone = f"({area_code}) {prefix}-{line}"
            
            domain_name = name.lower().replace(" ", "").replace("&", "and")
            website = f"https://www.{domain_name}.com"
            address = f"{random.randint(100, 9999)} {fake.street_name()}, {loc_title}, TX {random.randint(75000, 79999)}"
            
            candidates.append(RawBusinessCandidate(
                name=name,
                address=address,
                phone=phone,
                website=website,
                source_name=self.source_name,
                source_url=f"https://www.yellowpages.com/biz/{domain_name}",
            ))
            
        return candidates
