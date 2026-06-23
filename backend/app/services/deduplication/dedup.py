from typing import List, Set
from urllib.parse import urlparse
from rapidfuzz import fuzz
from loguru import logger
from app.services.search.adapters.base import RawBusinessCandidate

def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    # Extract only digits
    digits = "".join(filter(str.isdigit, phone))
    # Standardize US phone length (remove leading 1 if 11 digits)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits

def extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

class Deduplicator:
    def group_candidates(self, candidates: List[RawBusinessCandidate]) -> List[List[RawBusinessCandidate]]:
        """
        Groups raw business candidates that represent the same business.
        Uses fuzzy matching on name, phone numbers, domains, and address similarity.
        
        Returns:
            List[List[RawBusinessCandidate]]: A list of candidate groups.
        """
        if not candidates:
            return []

        groups: List[List[RawBusinessCandidate]] = []
        
        for candidate in candidates:
            matched_group_idx = -1
            
            for idx, group in enumerate(groups):
                if self._are_duplicates(candidate, group):
                    matched_group_idx = idx
                    break
                    
            if matched_group_idx != -1:
                groups[matched_group_idx].append(candidate)
            else:
                groups.append([candidate])
                
        duplicates_removed = len(candidates) - len(groups)
        logger.info(f"Deduplicator: Grouped {len(candidates)} candidates into {len(groups)} unique entities. Removed {duplicates_removed} duplicates.")
        return groups

    def _are_duplicates(self, candidate: RawBusinessCandidate, group: List[RawBusinessCandidate]) -> bool:
        """
        Compares candidate against all items in a group to see if it belongs there.
        """
        cand_phone = normalize_phone(candidate.phone)
        cand_domain = extract_domain(candidate.website)
        cand_name = candidate.name.lower().strip()
        
        for member in group:
            memb_phone = normalize_phone(member.phone)
            memb_domain = extract_domain(member.website)
            memb_name = member.name.lower().strip()

            # 1. Exact phone match (very strong signal)
            if cand_phone and memb_phone and cand_phone == memb_phone:
                return True

            # 2. Domain match + high name similarity
            if cand_domain and memb_domain and cand_domain == memb_domain:
                # If they share the exact domain, a lower name similarity is sufficient
                name_sim = fuzz.token_sort_ratio(cand_name, memb_name)
                if name_sim >= 60.0:
                    return True

            # 3. High name similarity + similar address or details
            name_sim = fuzz.token_sort_ratio(cand_name, memb_name)
            
            # If name similarity is extremely high
            if name_sim >= 85.0:
                # Verify address doesn't conflict completely
                if candidate.address and member.address:
                    addr_sim = fuzz.token_sort_ratio(candidate.address.lower(), member.address.lower())
                    if addr_sim >= 50.0:
                        return True
                else:
                    # If one of them lacks an address, assume match since names are so close
                    return True

            # 4. Partial name similarity + address match
            if name_sim >= 65.0 and candidate.address and member.address:
                addr_sim = fuzz.token_sort_ratio(candidate.address.lower(), member.address.lower())
                if addr_sim >= 75.0:
                    return True

        return False
global_deduplicator = Deduplicator()
