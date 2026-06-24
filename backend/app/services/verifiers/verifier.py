from typing import List, Dict, Any, Tuple
from loguru import logger
from app.services.search.adapters.base import RawBusinessCandidate
from app.schemas.schemas import BusinessCreate

# Source weights as requested in reliability scoring
SOURCE_WEIGHTS = {
    "website": 100,
    "official_website": 100,
    "government": 95,
    "association": 90,
    "linkedin": 85,
    "yelp": 80,
    "yellowpages": 60,
    "facebook": 70,
    "duckduckgo": 60,
    "healthgrades": 90,
    "avvo": 90,
    "angi": 80,
    "unknown": 60
}

def get_source_weight(source_name: str) -> int:
    name_lower = source_name.lower()
    for key, weight in SOURCE_WEIGHTS.items():
        if key in name_lower:
            return weight
    return 60

class VerificationEngine:
    def verify_and_merge(
        self, 
        candidates: List[RawBusinessCandidate], 
        website_details: Dict[str, Any] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Takes raw candidates from different sources for what is determined to be the same business,
        plus optional official website crawl details, and merges them.
        Detects conflicts and computes field sources and verification score.
        
        Returns:
            - merged_data: dict representing the merged Business
            - conflicts: list of dict representing found conflicts
        """
        if not candidates:
            return {}, []

        # 1. Collect all values for each field from all sources
        field_values: Dict[str, Dict[str, List[str]]] = {
            "phone": {},
            "address": {},
            "email": {},
            "website": {},
            "working_hours": {}
        }
        
        # Helper to record a field value and its source
        def record_field(field_name: str, value: Any, source_name: str, source_url: str):
            if not value:
                return
            
            # For lists or dicts, stringify for matching, but handle dicts specially
            val_str = str(value).strip()
            if not val_str:
                return
                
            # Basic normalization for phone numbers
            if field_name == "phone":
                has_plus = val_str.strip().startswith("+")
                digits = "".join(filter(str.isdigit, val_str))
                
                # Smart check if it looks like a US number vs international (e.g. Indian) number
                is_us = False
                if len(digits) == 10:
                    # Look at candidates' addresses to see if it contains Indian keywords
                    is_indian = any(
                        cand.address and any(k in cand.address.lower() for k in ["india", "tamil", "karnataka", "delhi", "mumbai", "chennai", "bangalore", "630"])
                        for cand in candidates
                    )
                    if not is_indian:
                        is_us = True
                elif len(digits) == 11 and digits.startswith("1"):
                    is_us = True
                
                if is_us:
                    if len(digits) == 10:
                        val_str = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                    elif len(digits) == 11:
                        val_str = f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
                else:
                    # Non-US number: preserve digits, add leading + back if original had it
                    val_str = ("+" if has_plus else "") + digits
                    
            if val_str not in field_values[field_name]:
                field_values[field_name][val_str] = []
            
            field_values[field_name][val_str].append(source_url or source_name)

        # Record from candidates
        for cand in candidates:
            src_name = cand.source_name
            src_url = cand.source_url
            if getattr(cand, "is_simulated", False):
                src_name = f"{src_name}_simulated"
                if src_url:
                    src_url = f"{src_url}#simulated"
                else:
                    src_url = f"simulated://{cand.source_name}"
            record_field("phone", cand.phone, src_name, src_url)
            record_field("address", cand.address, src_name, src_url)
            record_field("email", cand.email, src_name, src_url)
            record_field("website", cand.website, src_name, src_url)
            record_field("working_hours", cand.working_hours, src_name, src_url)

        # Record from official website details (if we crawled it)
        if website_details:
            site_url = website_details.get("website_url") or candidates[0].website or "website"
            record_field("phone", website_details.get("phone"), "official_website", site_url)
            record_field("address", website_details.get("address"), "official_website", site_url)
            record_field("email", website_details.get("email"), "official_website", site_url)
            record_field("working_hours", website_details.get("working_hours"), "official_website", site_url)

        # 2. Resolve fields and detect conflicts
        resolved_fields = {}
        conflicts_list = []
        source_urls_mapping = {}

        for field_name, values_dict in field_values.items():
            if not values_dict:
                resolved_fields[field_name] = None
                source_urls_mapping[field_name] = []
                continue

            unique_values = list(values_dict.keys())
            
            # Map field value back to its original object if it was converted to string
            # (especially for working_hours)
            def get_original_val(val_str: str):
                if field_name == "working_hours":
                    # Find working hours object
                    for cand in candidates:
                        if cand.working_hours and str(cand.working_hours).strip() == val_str:
                            return cand.working_hours
                    if website_details and website_details.get("working_hours") and str(website_details.get("working_hours")).strip() == val_str:
                        return website_details.get("working_hours")
                return val_str

            if len(unique_values) == 1:
                # No conflict
                val_str = unique_values[0]
                resolved_fields[field_name] = get_original_val(val_str)
                source_urls_mapping[field_name] = values_dict[val_str]
            else:
                # Conflict detected!
                logger.warning(f"VerificationEngine: Conflict detected on field '{field_name}' with values: {unique_values}")
                conflicts_list.append({
                    "field_name": field_name,
                    "conflicting_values": unique_values,
                    "resolved": False
                })
                
                # Determine "best" value based on the highest weight of its sources
                best_value = None
                best_weight = -1
                best_sources = []
                
                for val_str, sources in values_dict.items():
                    # Calculate max weight among the sources for this value
                    max_w = -1
                    for src in sources:
                        # Extract source name from url or text
                        src_name = "unknown"
                        for name in SOURCE_WEIGHTS.keys():
                            if name in src.lower():
                                src_name = name
                                break
                        w = get_source_weight(src_name)
                        if w > max_w:
                            max_w = w
                    
                    if max_w > best_weight:
                        best_weight = max_w
                        best_value = val_str
                        best_sources = sources
                        
                resolved_fields[field_name] = get_original_val(best_value)
                source_urls_mapping[field_name] = best_sources

        # 3. Handle non-conflicting lists (services, specialties, certifications, awards, social_profiles, images)
        # We merge these by taking the union of values across all sources.
        merged_services = set()
        merged_specialties = set()
        merged_certifications = set()
        merged_awards = set()
        merged_socials = set()
        merged_images = set()

        for cand in candidates:
            if cand.services:
                merged_services.update(cand.services)
            if cand.specialties:
                merged_specialties.update(cand.specialties)
            if cand.certifications:
                merged_certifications.update(cand.certifications)
            if cand.awards:
                merged_awards.update(cand.awards)
            if cand.social_profiles:
                merged_socials.update(cand.social_profiles)

        if website_details:
            merged_services.update(website_details.get("services", []))
            merged_specialties.update(website_details.get("specialties", []))
            merged_certifications.update(website_details.get("certifications", []))
            merged_awards.update(website_details.get("awards", []))
            merged_socials.update(website_details.get("social_profiles", []))

        # 4. Calculate Reliability / Verification Score
        # Verification score is based on:
        # - Number of sources verifying the primary fields (phone, address, website)
        # - Weight of those sources
        # Max score is 100.
        score_components = []
        
        # Check phone verification
        phone_sources = source_urls_mapping.get("phone", [])
        real_phone_sources = [s for s in phone_sources if "simulated" not in s.lower()]
        if real_phone_sources:
            # Score contribution based on max weight source
            max_w = max([get_source_weight(s.split("//")[-1].split("/")[0]) if "://" in s else get_source_weight(s) for s in real_phone_sources])
            # Multi-source bonus
            bonus = 15 if len(real_phone_sources) > 1 else 0
            score_components.append(min(max_w + bonus, 100))
        else:
            score_components.append(0)

        # Check website verification
        web_sources = source_urls_mapping.get("website", [])
        real_web_sources = [s for s in web_sources if "simulated" not in s.lower()]
        if real_web_sources:
            max_w = max([get_source_weight(s.split("//")[-1].split("/")[0]) if "://" in s else get_source_weight(s) for s in real_web_sources])
            bonus = 10 if len(real_web_sources) > 1 else 0
            score_components.append(min(max_w + bonus, 100))
        else:
            score_components.append(0)

        # Check address verification
        addr_sources = source_urls_mapping.get("address", [])
        real_addr_sources = [s for s in addr_sources if "simulated" not in s.lower()]
        if real_addr_sources:
            max_w = max([get_source_weight(s.split("//")[-1].split("/")[0]) if "://" in s else get_source_weight(s) for s in real_addr_sources])
            bonus = 10 if len(real_addr_sources) > 1 else 0
            score_components.append(min(max_w + bonus, 100))
        else:
            score_components.append(0)

        verification_score = round(sum(score_components) / len(score_components), 1) if score_components else 0.0

        # If it is entirely simulated candidates, cap the verification score at a low value (e.g. 5.0)
        # to prevent it from showing up as "highly verified"
        all_simulated = all(getattr(cand, "is_simulated", False) for cand in candidates)
        if all_simulated:
            verification_score = 5.0

        # Choose the most complete business name (the longest or first)
        names = [cand.name for cand in candidates if cand.name]
        business_name = max(names, key=len) if names else candidates[0].name

        # Average rating and total review counts
        ratings = [cand.rating for cand in candidates if cand.rating is not None]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None
        
        review_counts = [cand.review_count for cand in candidates if cand.review_count is not None]
        total_reviews = sum(review_counts) if review_counts else None

        merged_data = {
            "business_name": business_name,
            "address": resolved_fields.get("address"),
            "phone": resolved_fields.get("phone"),
            "email": resolved_fields.get("email"),
            "website": resolved_fields.get("website"),
            "working_hours": resolved_fields.get("working_hours") or {},
            "rating": avg_rating,
            "review_count": total_reviews,
            "services": list(merged_services),
            "specialties": list(merged_specialties),
            "license_information": None,  # Can be populated by specialized govt crawls later
            "certifications": list(merged_certifications),
            "awards": list(merged_awards),
            "social_profiles": list(merged_socials),
            "image_urls": list(merged_images),
            "source_urls": source_urls_mapping,
            "verification_score": verification_score
        }

        return merged_data, conflicts_list
global_verification_engine = VerificationEngine()
