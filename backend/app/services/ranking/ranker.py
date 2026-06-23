import math
from typing import List, Dict, Any

class RankingEngine:
    def rank_businesses(self, businesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ranks a list of businesses based on:
        1. Verification score (weight: 40%)
        2. Website existence (weight: 15%)
        3. Reviews (rating * log(review_count), weight: 15%)
        4. Completeness (fraction of non-null fields, weight: 15%)
        5. Source count (weight: 15%)
        
        Returns:
            List[Dict[str, Any]]: Sorted list of businesses descending by rank score.
        """
        scored_businesses = []
        for biz in businesses:
            score = self.calculate_rank_score(biz)
            # Add rank score to business dict for transparency in UI
            biz_copy = dict(biz)
            biz_copy["rank_score"] = round(score, 2)
            scored_businesses.append(biz_copy)
            
        # Sort descending
        return sorted(scored_businesses, key=lambda x: x["rank_score"], reverse=True)

    def calculate_rank_score(self, biz: Dict[str, Any]) -> float:
        # 1. Verification score (0 to 100)
        v_score = biz.get("verification_score", 0.0)
        
        # 2. Website existence (100 if website present, else 0)
        web_score = 100.0 if biz.get("website") else 0.0
        
        # 3. Reviews (Rating [0-5] * log(Review Count), normalized to 0-100 scale)
        rating = biz.get("rating") or 0.0
        review_count = biz.get("review_count") or 0
        if rating > 0 and review_count > 0:
            # max review score is approx 5 * ln(1000) = 34.5
            rev_score = rating * math.log(review_count + 1)
            # scale to 0-100 (cap at 100)
            rev_score = min((rev_score / 35.0) * 100.0, 100.0)
        else:
            rev_score = 0.0
            
        # 4. Completeness score (0 to 100)
        completeness_score = self.calculate_completeness(biz)
        
        # 5. Source count (0 to 100 based on number of sources, maxed at 5 sources)
        source_urls = biz.get("source_urls") or {}
        # Union of all sources across all fields
        all_sources = set()
        for field, sources in source_urls.items():
            if isinstance(sources, list):
                all_sources.update(sources)
        src_count = len(all_sources)
        src_score = min((src_count / 5.0) * 100.0, 100.0)

        # Weighted sum
        total_score = (
            (v_score * 0.40) +
            (web_score * 0.15) +
            (rev_score * 0.15) +
            (completeness_score * 0.15) +
            (src_score * 0.15)
        )
        return total_score

    def calculate_completeness(self, biz: Dict[str, Any]) -> float:
        # Key fields we check for completeness
        fields_to_check = [
            "address", "phone", "email", "website", 
            "working_hours", "rating", "review_count", 
            "services", "specialties", "certifications", 
            "awards", "social_profiles"
        ]
        
        filled_count = 0
        for f in fields_to_check:
            val = biz.get(f)
            if val is not None:
                if isinstance(val, list) and not val:
                    continue
                if isinstance(val, dict) and not val:
                    continue
                if isinstance(val, str) and not val.strip():
                    continue
                filled_count += 1
                
        return (filled_count / len(fields_to_check)) * 100.0
global_ranking_engine = RankingEngine()
