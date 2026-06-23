import re
from typing import Dict, Optional

def parse_query(query: str) -> Dict[str, Optional[str]]:
    """
    Parses a query string (e.g. 'Cardiologists in Birmingham' or 'Dallas plumbers')
    and extracts the 'category' and 'location'.
    """
    query = query.strip()
    
    # Check for "in", "near", "around", "at" patterns (case-insensitive)
    pattern = re.compile(r'\b(in|near|around|at)\b', re.IGNORECASE)
    match = pattern.search(query)
    
    if match:
        idx = match.start()
        category = query[:idx].strip()
        location = query[match.end():].strip()
        
        # Clean up any trailing punctuation
        category = re.sub(r'[^\w\s-]', '', category)
        location = re.sub(r'[^\w\s-]', '', location)
        
        if category and location:
            return {"category": category, "location": location}
            
    # Check for suffix locations e.g. "Chicago plumbers" where Chicago starts with a capital letter
    # Or "Birmingham cardiologists"
    words = query.split()
    if len(words) >= 2:
        # If the first word is capitalized and represents a potential location,
        # and the rest are lowercase or mixed representing category.
        # e.g., "Austin Dentist"
        # Let's try splitting: if first word is capitalized, it might be the location.
        # Let's look for common patterns.
        # Also check if last word is capitalized: "Dentist Austin"
        if words[0][0].isupper() and not words[-1][0].isupper():
            # First word is capitalized, e.g. "Birmingham cardiologists"
            return {
                "category": " ".join(words[1:]).strip(),
                "location": words[0].strip()
            }
        elif words[-1][0].isupper() and not words[0][0].isupper():
            # Last word is capitalized, e.g. "cardiologists Birmingham"
            return {
                "category": " ".join(words[:-1]).strip(),
                "location": words[-1].strip()
            }
            
    # Default fallback: category is the whole query, location is None
    # We clean it up
    cleaned = re.sub(r'[^\w\s-]', '', query)
    return {
        "category": cleaned,
        "location": None
    }
