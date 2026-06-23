from typing import List, Dict, Any

class ReportGenerator:
    def generate_analytics(self, businesses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes completeness metrics and counts for analytics.
        """
        total = len(businesses)
        if total == 0:
            return {
                "records_with_phone": 0,
                "records_with_website": 0,
                "records_with_hours": 0,
                "records_with_license": 0,
                "total_records": 0,
                "phone_coverage_pct": 0.0,
                "website_coverage_pct": 0.0,
                "hours_coverage_pct": 0.0,
                "license_coverage_pct": 0.0
            }

        with_phone = sum(1 for b in businesses if b.get("phone"))
        with_website = sum(1 for b in businesses if b.get("website"))
        with_hours = sum(1 for b in businesses if b.get("working_hours"))
        with_license = sum(1 for b in businesses if b.get("license_information"))

        return {
            "records_with_phone": with_phone,
            "records_with_website": with_website,
            "records_with_hours": with_hours,
            "records_with_license": with_license,
            "total_records": total,
            "phone_coverage_pct": round((with_phone / total) * 100.0, 1),
            "website_coverage_pct": round((with_website / total) * 100.0, 1),
            "hours_coverage_pct": round((with_hours / total) * 100.0, 1),
            "license_coverage_pct": round((with_license / total) * 100.0, 1)
        }

    def generate_markdown_report(
        self,
        query_text: str,
        businesses: List[Dict[str, Any]],
        duplicates_removed: int,
        duration: float,
        sources_count: int
    ) -> str:
        """
        Creates a markdown report summarizing the research findings.
        """
        total_found = len(businesses) + duplicates_removed
        verified_count = sum(1 for b in businesses if b.get("verification_score", 0.0) >= 70.0)
        
        analytics = self.generate_analytics(businesses)
        
        # Determine average rating
        ratings = [b.get("rating") for b in businesses if b.get("rating") is not None]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else "N/A"

        md = f"""# Research Report: {query_text}

## Executive Summary
This report summarizes the discoveries and field-level verification for the query **"{query_text}"**. 
An autonomous crawling agent extracted business profiles, cross-checked contact numbers against local and global directory profiles, and performed fuzzy deduplication.

---

## Research Statistics
* **Query:** {query_text}
* **Businesses Discovered:** {total_found}
* **Unique Verified Entities:** {len(businesses)}
* **Highly Verified (Score >= 70):** {verified_count}
* **Duplicates Removed:** {duplicates_removed}
* **Sources Utilized:** {sources_count}
* **Duration:** {duration:.2f} seconds
* **Average User Rating:** {avg_rating} ⭐

---

## Data Quality & Coverage Summary
The table below represents the presence and verification of critical business fields across all matched records.

| Field | Matches Found | Coverage % |
| :--- | :---: | :---: |
| **Phone Number** | {analytics["records_with_phone"]} | {analytics["phone_coverage_pct"]}% |
| **Website Link** | {analytics["records_with_website"]} | {analytics["website_coverage_pct"]}% |
| **Working Hours** | {analytics["records_with_hours"]} | {analytics["hours_coverage_pct"]}% |
| **Professional License** | {analytics["records_with_license"]} | {analytics["license_coverage_pct"]}% |

---

## Top Verified Businesses
Here are the top 5 businesses ranked by reliability, source count, and completeness:

"""
        # Take top 5
        top_businesses = sorted(businesses, key=lambda x: x.get("verification_score", 0.0), reverse=True)[:5]
        for idx, biz in enumerate(top_businesses, 1):
            phone_str = biz.get("phone") or "N/A"
            web_str = f"[{biz.get('website')}]({biz.get('website')})" if biz.get("website") else "N/A"
            md += f"{idx}. **{biz.get('business_name')}** (Verification Score: {biz.get('verification_score')}/100)\n"
            md += f"   - Phone: {phone_str}\n"
            md += f"   - Website: {web_str}\n"
            md += f"   - Address: {biz.get('address') or 'N/A'}\n"
            
        md += """
---
*Report generated automatically by the AI-powered Business Research Agent.*
"""
        return md.strip()
global_report_generator = ReportGenerator()
