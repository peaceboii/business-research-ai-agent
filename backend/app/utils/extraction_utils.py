import re
from typing import Optional

# Compiled patterns
PHONE_PATTERN = re.compile(
    r'(?:'
    # US format with area code
    r'(?:\+?1[-.\s]?)?\(?([2-9][0-8][0-9])\)?[-.\s]?([2-9][0-9]{2})[-.\s]?([0-9]{4})'
    r'|'
    # Indian / International with country code +91 or similar
    r'\+?[91]{2,3}[-.\s]?\(?[0-9]{2,5}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{4,6}'
    r'|'
    # International general
    r'\+?[0-9]{1,4}[-.\s]?\(?[0-9]{2,5}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,6}'
    r'|'
    # Indian mobile: 10 digits starting with 6-9
    r'\b[6-9]\d{9}\b'
    r'|'
    # Indian landline or other formats
    r'\b\d{2,5}[-.\s]?\d{5,8}\b'
    r')'
)

# Address markers and regexes
ADDRESS_US_PATTERN = re.compile(
    r'\b\d{1,5}[,\s]+[A-Za-z0-9\s,\.]{3,50},\s*[A-Za-z\s]{2,20},\s*[A-Z]{2}(?:\s+\d{5}(?:-\d{4})?)?\b',
    re.IGNORECASE
)

ADDRESS_MARKERS_PATTERN = re.compile(
    r'\b\d{1,5}[,\s]+[A-Za-z0-9\s,\.]{2,40}\b(?:Road|Rd|Street|St|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Highway|Hwy|Nagar|Puram|Complex|Bldg|Building|Floor|Block|Colony|Plaza|Sector|Zone)\b[A-Za-z0-9\s,\.]{0,50}(?:\b\d{5,6}\b)?',
    re.IGNORECASE
)

def extract_phone_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    
    # Clean text to avoid issues with some HTML characters
    cleaned_text = text.replace('&nbsp;', ' ').replace('&AMP;', '&').replace('&amp;', '&')
    
    # Search for phone number
    match = PHONE_PATTERN.search(cleaned_text)
    if match:
        val = match.group(0).strip()
        # Clean any trailing/leading punctuation that isn't part of a phone number
        val = re.sub(r'^[^\d+({]+|[^\d)]+$', '', val)
        # Verify it has at least 7 digits
        digits = re.sub(r'\D', '', val)
        if len(digits) >= 7 and len(digits) <= 15:
            return val
            
    return None

def extract_address_from_text(text: str) -> Optional[str]:
    if not text:
        return None
        
    # Split text into lines to avoid matching across distinct paragraphs
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # 1. Try explicit markers on each line
    explicit_pat = re.compile(r'\b(?:address|location|office|hq|headquarters|clinic|hospital)\b\s*:?\s*(.*)', re.IGNORECASE)
    for i, line in enumerate(lines):
        match = explicit_pat.match(line)
        if match:
            candidate = match.group(1).strip()
            if _is_valid_address(candidate):
                return candidate
            # If next line is a good continuation
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if len(next_line) > 10 and not any(kw in next_line.lower() for kw in ['phone', 'email', 'website', 'fax', 'social']):
                    if _is_valid_address(next_line):
                        return next_line
                    combined = f"{candidate}, {next_line}"
                    if _is_valid_address(combined):
                        return combined

    # 2. Try matching full US address pattern
    for line in lines:
        match = ADDRESS_US_PATTERN.search(line)
        if match:
            candidate = match.group(0).strip()
            if _is_valid_address(candidate):
                return candidate
                
    # 3. Try matching using address suffix markers
    for line in lines:
        match = ADDRESS_MARKERS_PATTERN.search(line)
        if match:
            candidate = match.group(0).strip()
            if _is_valid_address(candidate):
                return candidate
                
    # 4. Fallback search on whole text (lines joined by comma) if line-by-line failed
    combined_text = ", ".join(lines)
    match = ADDRESS_US_PATTERN.search(combined_text)
    if match and _is_valid_address(match.group(0).strip()):
        return match.group(0).strip()
        
    match = ADDRESS_MARKERS_PATTERN.search(combined_text)
    if match and _is_valid_address(match.group(0).strip()):
        return match.group(0).strip()

    return None

def _is_valid_address(candidate: str) -> bool:
    if not candidate or len(candidate) < 10 or len(candidate) > 200:
        return False
        
    # Reject strings that are clearly not addresses
    reject_patterns = [
        r'^(showroom|shop|space|rent|buy|sell|service|product|contact|about|home|menu|login|sign)',
        r'^(click|view|read|learn|more|get|find|search|browse|explore)',
        r'^(our |we |the |this |these |those |a |an )',
        r'^(top |best |leading |premier |no\.\s*1 )',
    ]
    candidate_lower = candidate.lower().strip()
    for pat in reject_patterns:
        if re.match(pat, candidate_lower):
            return False
            
    # Must contain at least one digit (house number, zip code, etc.) unless it has strong address markers
    has_digit = bool(re.search(r'\d', candidate))
    strong_markers = ['street', 'road', 'avenue', 'boulevard', 'lane', 'drive', 
                     'nagar', 'puram', 'colony', 'complex', 'sector', 'block',
                     'floor', 'suite', 'building', 'plaza', 'circle', 'highway',
                     'cross', 'main', 'layout', 'extension', 'phase']
    has_strong_marker = any(m in candidate_lower for m in strong_markers)
    
    if not has_digit and not has_strong_marker:
        return False
        
    # Should contain a comma, or a strong address marker, or a zip/postal code
    has_comma = ',' in candidate
    has_zip = bool(re.search(r'\b\d{5,6}\b', candidate))
    
    if not has_comma and not has_zip and not has_strong_marker:
        if not re.match(r'^\d+\s+\w', candidate):
            return False
            
    return True
