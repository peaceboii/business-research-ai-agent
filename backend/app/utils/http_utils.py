import asyncio
import random
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from typing import Dict, Optional, Any
import httpx
from loguru import logger

# Static fallback list of user agents in case fake-useragent fails
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# Cache robots.txt parsers
ROBOTS_CACHE: Dict[str, RobotFileParser] = {}
ROBOTS_CACHE_TIME: Dict[str, float] = {}
CACHE_TTL = 3600  # 1 hour

def get_random_user_agent() -> str:
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        return ua.random
    except Exception:
        return random.choice(USER_AGENTS)

async def check_robots_txt(url: str, user_agent: str = "*") -> bool:
    """
    Checks robots.txt for the given URL.
    Returns True if scraping is allowed, False otherwise.
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{base_url}/robots.txt"
    
    current_time = time.time()
    
    # Return cached parser if valid
    if base_url in ROBOTS_CACHE and (current_time - ROBOTS_CACHE_TIME.get(base_url, 0)) < CACHE_TTL:
        parser = ROBOTS_CACHE[base_url]
        return parser.can_fetch(user_agent, url)
        
    parser = RobotFileParser()
    parser.set_url(robots_url)
    
    try:
        # Fetch robots.txt using httpx asynchronously
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(robots_url, headers={"User-Agent": get_random_user_agent()})
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                # If robots.txt doesn't exist or is inaccessible, assume allowed
                parser.allow_all = True
    except Exception as e:
        logger.warning(f"Error fetching robots.txt from {robots_url}: {e}. Assuming allowed.")
        parser.allow_all = True
        
    ROBOTS_CACHE[base_url] = parser
    ROBOTS_CACHE_TIME[base_url] = current_time
    
    return parser.can_fetch(user_agent, url)


class RateLimiter:
    """
    Simple per-domain rate limiter to avoid overloading targets.
    """
    def __init__(self, delay_seconds: float = 1.0):
        self.delay_seconds = delay_seconds
        self.last_request_times: Dict[str, float] = {}
        self.lock = asyncio.Lock()

    async def wait_if_needed(self, url: str):
        parsed = urlparse(url)
        domain = parsed.netloc
        
        async with self.lock:
            last_time = self.last_request_times.get(domain, 0.0)
            elapsed = time.time() - last_time
            if elapsed < self.delay_seconds:
                wait_time = self.delay_seconds - elapsed
                logger.info(f"RateLimiter: Sleeping {wait_time:.2f}s for domain {domain}")
                await asyncio.sleep(wait_time)
            self.last_request_times[domain] = time.time()

global_rate_limiter = RateLimiter(delay_seconds=1.5)


async def http_get_with_retry(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    retries: int = 3,
    timeout: float = 15.0,
    check_robots: bool = True
) -> Optional[httpx.Response]:
    """
    Wrapper for HTTP GET requests with rotating User-Agent, robots.txt checks,
    rate limiting, and retries.
    """
    if check_robots:
        allowed = await check_robots_txt(url)
        if not allowed:
            logger.warning(f"Access forbidden by robots.txt for URL: {url}")
            return None
            
    await global_rate_limiter.wait_if_needed(url)
    
    req_headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }
    if headers:
        req_headers.update(headers)
        
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=req_headers, params=params)
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"Request to {url} failed with status {response.status_code}. Attempt {attempt}/{retries}")
        except httpx.RequestError as e:
            logger.warning(f"HTTP request error: {e}. Attempt {attempt}/{retries}")
            
        if attempt < retries:
            await asyncio.sleep(2.0 ** attempt)  # Exponential backoff
            
    logger.error(f"Failed to fetch {url} after {retries} attempts.")
    return None
