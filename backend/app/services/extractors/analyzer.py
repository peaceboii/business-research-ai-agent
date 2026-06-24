import asyncio
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import httpx
from loguru import logger
from app.utils.http_utils import get_random_user_agent, check_robots_txt

class WebsiteAnalyzer:
    def __init__(self):
        # Compiled patterns for extraction
        self.phone_pattern = re.compile(
            r'(?:'
            r'(?:\+?1[-.\s]?)?\(?([2-9][0-8][0-9])\)?[-.\s]?([2-9][0-9]{2})[-.\s]?([0-9]{4})'
            r'|'
            r'\+?[91]{2,3}[-.\s]?\(?[0-9]{2,5}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{4,6}'
            r'|'
            r'\+?[0-9]{1,4}[-.\s]?\(?[0-9]{2,5}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,6}'
            r'|'
            r'\b[6-9]\d{9}\b'
            r'|'
            r'\b\d{2,5}[-.\s]?\d{5,8}\b'
            r')'
        )
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.social_patterns = [
            "facebook.com", "linkedin.com", "twitter.com", "x.com", 
            "instagram.com", "youtube.com", "pinterest.com", "yelp.com"
        ]

    async def analyze_website(self, url: str) -> Dict[str, Any]:
        """
        Analyze a business's official website.
        Attempts fast fetch with httpx + BeautifulSoup first.
        If it fails, lacks text, or uses JS, falls back to Playwright.
        """
        if not url:
            return {}

        if not url.startswith("http"):
            url = "https://" + url

        logger.info(f"WebsiteAnalyzer: Starting analysis for {url}")
        
        # Check robots.txt
        allowed = await check_robots_txt(url)
        if not allowed:
            logger.warning(f"WebsiteAnalyzer: Scraping forbidden by robots.txt for {url}")
            return {}

        html_content = ""
        used_playwright = False

        # Attempt 1: httpx + BeautifulSoup (fast)
        try:
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    html_content = response.text
                    # Check if body is mostly empty (potential SPA)
                    soup = BeautifulSoup(html_content, "html.parser")
                    text_len = len(soup.get_text(strip=True))
                    if text_len < 300:
                        logger.info(f"WebsiteAnalyzer: Text content too short ({text_len} chars). Falling back to Playwright.")
                        html_content = ""  # Force fallback
                else:
                    logger.warning(f"WebsiteAnalyzer: HTTP fetch returned status {response.status_code} for {url}")
        except Exception as e:
            logger.warning(f"WebsiteAnalyzer: Fast fetch failed for {url}: {e}. Trying Playwright fallback...")

        # Attempt 2: Playwright headless browser fallback
        if not html_content:
            try:
                html_content = await self._fetch_with_playwright(url)
                used_playwright = True
            except Exception as e:
                logger.error(f"WebsiteAnalyzer: Playwright fallback failed for {url}: {e}")

        if not html_content:
            logger.warning(f"WebsiteAnalyzer: No HTML content retrieved for {url}")
            return {}

        # Parse extracted HTML
        soup = BeautifulSoup(html_content, "html.parser")
        data = self._parse_html(soup, html_content)
        data["used_playwright"] = used_playwright

        # If address or phone is missing, follow contact/locations page to be thorough
        if not data.get("address") or not data.get("phone"):
            contact_url = self._find_contact_link(soup, url)
            if contact_url:
                logger.info(f"WebsiteAnalyzer: Address/phone missing on homepage. Crawling contact/locations: {contact_url}")
                try:
                    contact_html = ""
                    if used_playwright:
                        contact_html = await self._fetch_with_playwright(contact_url)
                    else:
                        headers = {
                            "User-Agent": get_random_user_agent(),
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                        }
                        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                            res = await client.get(contact_url, headers=headers)
                            if res.status_code == 200:
                                contact_html = res.text
                    
                    if contact_html:
                        contact_soup = BeautifulSoup(contact_html, "html.parser")
                        contact_data = self._parse_html(contact_soup, contact_html)
                        
                        # Merge fields if missing
                        for field in ["phone", "email", "address", "working_hours"]:
                            if not data.get(field) and contact_data.get(field):
                                data[field] = contact_data[field]
                        
                        # Merge list fields
                        for field in ["services", "specialties", "certifications", "awards", "social_profiles"]:
                            if contact_data.get(field):
                                merged = list(set(data.get(field, []) + contact_data[field]))
                                data[field] = merged[:10]
                except Exception as e:
                    logger.warning(f"WebsiteAnalyzer: Failed to crawl contact page {contact_url}: {e}")

        logger.info(f"WebsiteAnalyzer: Extraction successful for {url}. Extracted phone: {data.get('phone')}, email: {data.get('email')}")
        return data

    def _find_contact_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        from urllib.parse import urljoin
        keywords = ["contact", "location", "address", "find-us", "reach-us", "about"]
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True).lower()
            if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("tel:") or href.startswith("mailto:"):
                continue
            if any(kw in text or kw in href.lower() for kw in keywords):
                return urljoin(base_url, a["href"])
        return None


    async def _fetch_with_playwright(self, url: str) -> str:
        """
        Loads the site using Playwright to render client-side JS.
        """
        from playwright.async_api import async_playwright
        
        logger.info(f"WebsiteAnalyzer: Launching Playwright browser for {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            try:
                # Wait up to 15s for the page to load
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                # Additional wait to let AJAX run
                await asyncio.sleep(3)
                content = await page.content()
                return content
            finally:
                await context.close()
                await browser.close()

    def _parse_html(self, soup: BeautifulSoup, raw_html: str) -> Dict[str, Any]:
        text_content = soup.get_text("\n")
        
        # Phone extraction
        phones = []
        for match in self.phone_pattern.finditer(text_content):
            if match.group(1) and match.group(2) and match.group(3):
                formatted = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
            else:
                num = match.group(0).strip()
                num = re.sub(r'^[^\d+({]+|[^\d)]+$', '', num)
                formatted = num
            if len(re.sub(r'\D', '', formatted)) >= 7:
                phones.append(formatted)
        
        phone = phones[0] if phones else None

        # Email extraction
        emails = self.email_pattern.findall(text_content)
        # Filter out common false positives like logo png/jpg
        emails = [e for e in emails if not any(e.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"])]
        email = emails[0].lower() if emails else None

        # Social profiles
        social_profiles = []
        for link in soup.find_all("a", href=True):
            href = link["href"].lower()
            if any(platform in href for platform in self.social_patterns):
                # Ensure it's a full URL and clean it up
                if href.startswith("/") or href.startswith("#"):
                    continue
                social_profiles.append(link["href"])
        
        # Deduplicate social profiles
        social_profiles = list(set(social_profiles))

        # Working Hours
        working_hours = self._extract_working_hours(text_content)

        # Address extraction
        address = self._extract_address(text_content)

        # Services, Certifications, Awards
        services = self._extract_list_by_keywords(soup, text_content, ["service", "treatment", "repair", "expertise", "specialty"])
        certifications = self._extract_list_by_keywords(soup, text_content, ["certif", "license", "accredit", "board certified"])
        awards = self._extract_list_by_keywords(soup, text_content, ["award", "recipient", "winner", "top doctor", "super lawyer"])

        return {
            "phone": phone,
            "email": email,
            "address": address,
            "working_hours": working_hours,
            "services": services[:10],  # cap at 10 items
            "specialties": services[:5],
            "certifications": certifications[:5],
            "awards": awards[:5],
            "social_profiles": social_profiles[:5],
        }

    def _extract_address(self, text: str) -> Optional[str]:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # 1. Try looking for "Address" or "Location" keyword explicitly
        pattern = re.compile(r'\b(?:address|location|office|hq|headquarters|clinic|hospital)\b\s*:?\s*(.*)', re.IGNORECASE)
        for i, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                address_candidate = match.group(1).strip()
                if len(address_candidate) > 10:
                    return address_candidate
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if len(next_line) > 10 and not any(kw in next_line.lower() for kw in ['phone', 'email', 'website', 'fax', 'social']):
                        if i + 2 < len(lines):
                            next_next_line = lines[i+2].strip()
                            if len(next_next_line) > 5 and (any(kw in next_next_line.lower() for kw in ['india', 'tamil', 'usa', 'state', 'pincode', 'zip', 'country', 'alabama', 'al', 'texas', 'tx']) or re.search(r'\b\d{5,6}\b', next_next_line)):
                                return f"{next_line}, {next_next_line}"
                        return next_line
                        
        # 2. Look for postal code patterns (5 or 6 digits) on lines with common address markers
        zip_pattern = re.compile(r'\b\d{5}(?:-\d{4})?\b|\b\d{6}\b')
        markers = [
            'street', 'road', 'st', 'rd', 'ave', 'blvd', 'lane', 'ln', 'drive', 'dr', 'way', 'court', 'ct', 
            'boulevard', 'highway', 'hwy', 'parkway', 'pkwy', 'suite', 'ste', 'plaza', 'circle', 'cir', 
            'loop', 'square', 'sq', 'floor', 'fl', 'building', 'bldg', 'box', 'po box', 'suite', 'nagar', 
            'complex', 'puram', 'colony'
        ]
        
        for i, line in enumerate(lines):
            if zip_pattern.search(line):
                # If the line contains a zip code and an address marker, return it
                if any(marker in line.lower() for marker in markers):
                    if len(line) > 15 and len(line) < 150:
                        return line
                # If the previous line contains an address marker, join them!
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if any(marker in prev_line.lower() for marker in markers):
                        if len(prev_line) > 5 and len(prev_line) < 100:
                            return f"{prev_line}, {line}"
                            
        # 3. Fallback: look for any line containing a zip code and starting with a number (likely house number)
        for line in lines:
            if zip_pattern.search(line) and re.match(r'^\d+\b', line):
                if len(line) > 15 and len(line) < 150:
                    return line
                    
        return None

    def _extract_working_hours(self, text: str) -> Dict[str, str]:
        """
        Look for hours-related phrases and parse them.
        """
        hours = {}
        # Simple heuristic parser
        # Look for matches like "Mon-Fri: 9:00 AM - 5:00 PM"
        pattern = re.compile(
            r'\b(Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?)\b.*?(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))',
            re.IGNORECASE
        )
        matches = pattern.findall(text)
        for day, hours_str in matches:
            day_clean = day.strip().title()
            if day_clean not in hours:
                hours[day_clean] = hours_str.strip()

        # Fallback to "Monday - Friday" generic block if individual days fail
        if not hours:
            fallback_pattern = re.compile(
                r'\b(Monday\s*-\s*Friday|Mon\s*-\s*Fri|Mon-Fri)\b.*?(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))',
                re.IGNORECASE
            )
            match = fallback_pattern.search(text)
            if match:
                hours["Mon-Fri"] = match.group(2).strip()
                
            # Check weekend
            weekend_pattern = re.compile(
                r'\b(Saturday\s*-\s*Sunday|Sat\s*-\s*Sun|Sat-Sun)\b.*?(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))',
                re.IGNORECASE
            )
            match_we = weekend_pattern.search(text)
            if match_we:
                hours["Sat-Sun"] = match_we.group(2).strip()

        return hours

    def _extract_list_by_keywords(self, soup: BeautifulSoup, text: str, keywords: List[str]) -> List[str]:
        """
        Finds paragraphs, list items, or sentences containing specific keywords and cleans them.
        """
        extracted = []
        # Find paragraphs or list items containing the keywords
        for elem in soup.find_all(["li", "p", "h3", "span"]):
            elem_text = elem.get_text(strip=True)
            if len(elem_text) > 4 and len(elem_text) < 100:
                if any(kw in elem_text.lower() for kw in keywords):
                    # Clean text
                    clean = re.sub(r'\s+', ' ', elem_text).strip()
                    if clean and clean not in extracted:
                        extracted.append(clean)
                        
        # Fallback: parse sentences from body text if list extraction is empty
        if not extracted:
            sentences = re.split(r'\.\s+', text)
            for sentence in sentences:
                if len(sentence) > 10 and len(sentence) < 120:
                    if any(kw in sentence.lower() for kw in keywords):
                        clean = sentence.strip()
                        if clean and clean not in extracted:
                            extracted.append(clean)

        return extracted
global_website_analyzer = WebsiteAnalyzer()
