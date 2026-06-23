import asyncio
import time
import datetime
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.models import Query, Business, BusinessSource, VerificationLog, Conflict, ResearchReport, CacheStat
from app.services.search.query_understanding import parse_query
from app.services.search.discovery import global_discovery_engine
from app.services.deduplication.dedup import global_deduplicator
from app.services.extractors.analyzer import global_website_analyzer
from app.services.verifiers.verifier import global_verification_engine
from app.services.ranking.ranker import global_ranking_engine
from app.services.cache.redis_cache import global_cache_service
from app.services.reporting.summary import global_report_generator

class ResearchRunner:
    async def run_research(
        self,
        query_text: str,
        db: Session,
        queue: Optional[asyncio.Queue] = None,
        query_id: Optional[int] = None
    ) -> Query:
        """
        Orchestrates the entire research pipeline:
        1. Parsing query
        2. Checking cache
        3. Concurrently discovering raw candidates
        4. Deduplicating candidates
        5. Running website analyzer and verifier in parallel
        6. Ranking businesses
        7. Generating markdown report & saving
        """
        start_time = time.time()
        
        # 1. Parse and create/update Query record
        parsed = parse_query(query_text)
        category = parsed.get("category") or "business"
        location = parsed.get("location") or "local"
        
        if query_id:
            query_record = db.query(Query).filter(Query.id == query_id).first()
            if query_record:
                query_record.category = category
                query_record.location = location
                query_record.status = "running"
                db.commit()
            else:
                query_record = Query(
                    query_text=query_text,
                    category=category,
                    location=location,
                    status="running"
                )
                db.add(query_record)
                db.commit()
                db.refresh(query_record)
        else:
            query_record = Query(
                query_text=query_text,
                category=category,
                location=location,
                status="running"
            )
            db.add(query_record)
            db.commit()
            db.refresh(query_record)
        
        logger.info(f"ResearchRunner: Starting run {query_record.id} for '{query_text}'")
        
        # Helper to publish events to SSE queue
        async def publish_event(status: str, message: str, data: Any = None):
            if queue:
                payload = {
                    "status": status,
                    "message": message,
                    "query_id": query_record.id,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "data": data
                }
                await queue.put(payload)
                # Small sleep to allow frontend smooth ingestion
                await asyncio.sleep(0.1)

        await publish_event("parsing", f"Parsed query: Category='{category}', Location='{location}'")
        
        # 2. Check Cache
        cache_key = f"query:{category.lower()}:{location.lower()}"
        cached_result = global_cache_service.get_json(cache_key)
        
        # Track Cache Statistics
        cache_stat = db.query(CacheStat).filter(CacheStat.key == cache_key).first()
        if not cache_stat:
            cache_stat = CacheStat(key=cache_key, hit_count=0, miss_count=0)
            db.add(cache_stat)
        else:
            if cache_stat.hit_count is None:
                cache_stat.hit_count = 0
            if cache_stat.miss_count is None:
                cache_stat.miss_count = 0
            
        if cached_result:
            logger.info(f"ResearchRunner: Cache hit for key '{cache_key}'")
            cache_stat.hit_count += 1
            db.commit()
            
            await publish_event("completed", "Loaded results from cache.", cached_result)
            query_record.status = "completed"
            db.commit()
            return query_record
            
        cache_stat.miss_count += 1
        db.commit()

        # 3. Discovery Stage
        await publish_event("discovering", f"Searching directories and search engines for '{category}' in '{location}'...")
        raw_candidates = await global_discovery_engine.run_discovery(category, location)
        
        if not raw_candidates:
            await publish_event("failed", "No businesses could be discovered.")
            query_record.status = "failed"
            db.commit()
            return query_record
            
        await publish_event("discovered", f"Found {len(raw_candidates)} business listings. Starting deduplication...")
        
        # 4. Deduplication Stage
        candidate_groups = global_deduplicator.group_candidates(raw_candidates)
        duplicates_removed = len(raw_candidates) - len(candidate_groups)
        
        await publish_event("deduplicated", f"Deduplication complete. Grouped into {len(candidate_groups)} unique entities. Removed {duplicates_removed} duplicates.")
        
        # 5. Website Crawl, Verification & Merging Stage
        processed_businesses = []
        
        # We process groups concurrently up to a concurrency limit to support thousands of records
        semaphore = asyncio.Semaphore(10)
        
        async def process_group(group: List[RawBusinessCandidate]):
            async with semaphore:
                # Get the first available website in the group to crawl
                website_url = next((c.website for c in group if c.website), None)
                website_details = None
                
                if website_url:
                    try:
                        # Enforce 15-second timeout on website crawl as per error handling
                        website_details = await asyncio.wait_for(
                            global_website_analyzer.analyze_website(website_url),
                            timeout=15.0
                        )
                        if website_details:
                            website_details["website_url"] = website_url
                    except Exception as e:
                        logger.error(f"ResearchRunner: Error analyzing website {website_url}: {e}")
                
                # Merge records and cross-check fields
                merged_data, conflicts_list = global_verification_engine.verify_and_merge(group, website_details)
                return merged_data, conflicts_list, group

        await publish_event("verifying", "Initiating verification and deep website analysis...")
        
        tasks = [process_group(group) for group in candidate_groups]
        results = await asyncio.gather(*tasks)
        
        # Save to database and construct output lists
        db_businesses = []
        all_conflicts = []
        sources_used = set()
        
        for merged_data, conflicts, group in results:
            if not merged_data:
                continue
                
            # Create Business ORM record
            biz_record = Business(
                query_id=query_record.id,
                business_name=merged_data["business_name"],
                address=merged_data["address"],
                phone=merged_data["phone"],
                email=merged_data["email"],
                website=merged_data["website"],
                working_hours=merged_data["working_hours"],
                rating=merged_data["rating"],
                review_count=merged_data["review_count"],
                services=merged_data["services"],
                specialties=merged_data["specialties"],
                license_information=merged_data["license_information"],
                certifications=merged_data["certifications"],
                awards=merged_data["awards"],
                social_profiles=merged_data["social_profiles"],
                image_urls=merged_data["image_urls"],
                source_urls=merged_data["source_urls"],
                verification_score=merged_data["verification_score"]
            )
            db.add(biz_record)
            db.commit()
            db.refresh(biz_record)
            
            # Save BusinessSource ORM records
            for cand in group:
                src_record = BusinessSource(
                    business_id=biz_record.id,
                    source_name=cand.source_name,
                    url=cand.source_url,
                    rating=cand.rating,
                    review_count=cand.review_count,
                    address=cand.address,
                    phone=cand.phone,
                    email=cand.email,
                    working_hours=cand.working_hours,
                    services=cand.services,
                    specialties=cand.specialties,
                    certifications=cand.certifications,
                    awards=cand.awards
                )
                db.add(src_record)
                if cand.source_url:
                    sources_used.add(cand.source_url)
                else:
                    sources_used.add(cand.source_name)
            
            # Save Conflict ORM records
            for conf in conflicts:
                conf_record = Conflict(
                    business_id=biz_record.id,
                    field_name=conf["field_name"],
                    conflicting_values=conf["conflicting_values"],
                    resolved=False
                )
                db.add(conf_record)
                all_conflicts.append(conf)

            # Save VerificationLog records for critical fields
            for field in ["phone", "address", "website", "email"]:
                sources = merged_data["source_urls"].get(field, [])
                for src in sources:
                    log_record = VerificationLog(
                        business_id=biz_record.id,
                        field_name=field,
                        source=src,
                        value=merged_data[field]
                    )
                    db.add(log_record)
                    
            db.commit()
            
            # For JSON serialization
            biz_dict = merged_data.copy()
            biz_dict["id"] = biz_record.id
            processed_businesses.append(biz_dict)
            
            # Progressive stream update: push business to SSE queue as they are discovered
            await publish_event("business_discovered", f"Verified & indexed: {biz_dict['business_name']}", biz_dict)

        # 6. Rank Results
        ranked_businesses = global_ranking_engine.rank_businesses(processed_businesses)
        
        # 7. Generate Research Report
        duration = time.time() - start_time
        num_sources = len(sources_used)
        
        markdown_report = global_report_generator.generate_markdown_report(
            query_text=query_text,
            businesses=ranked_businesses,
            duplicates_removed=duplicates_removed,
            duration=duration,
            sources_count=num_sources
        )
        
        # Compute coverage percentages
        analytics = global_report_generator.generate_analytics(ranked_businesses)
        
        report_record = ResearchReport(
            query_id=query_record.id,
            duration=duration,
            total_discovered=len(raw_candidates),
            total_verified=len(ranked_businesses),
            duplicates_removed=duplicates_removed,
            sources_used=num_sources,
            website_coverage=analytics["website_coverage_pct"],
            phone_coverage=analytics["phone_coverage_pct"],
            hours_coverage=analytics["hours_coverage_pct"],
            report_markdown=markdown_report
        )
        db.add(report_record)
        
        # Update Query status
        query_record.status = "completed"
        db.commit()
        db.refresh(report_record)
        
        # 8. Cache results
        cache_data = {
            "query_id": query_record.id,
            "businesses": ranked_businesses,
            "report_id": report_record.id,
            "report_markdown": markdown_report,
            "analytics": analytics
        }
        global_cache_service.set_json(cache_key, cache_data)
        
        await publish_event("completed", "Research run completed successfully!", cache_data)
        return query_record
global_research_runner = ResearchRunner()
