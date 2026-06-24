import asyncio
import io
import json
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
import pandas as pd
from loguru import logger

from app.database.connection import get_db
from app.models.models import Query as QueryModel, Business, BusinessSource, Conflict, ResearchReport, CacheStat
from app.schemas.schemas import (
    ResearchRequest, QueryResponse, BusinessResponse, ConflictResponse,
    ResearchReportResponse, AnalyticsResponse, StatsResponse, HealthResponse, ConflictResolveRequest
)
from app.services.research_runner import global_research_runner
from app.services.cache.redis_cache import global_cache_service
from app.services.reporting.summary import global_report_generator

router = APIRouter()

# Global dictionary to track SSE queues for active runs
active_queues = {}

@router.post("/research", response_model=QueryResponse, status_code=status.HTTP_201_CREATED)
def trigger_research(payload: ResearchRequest, db: Session = Depends(get_db)):
    """
    Triggers a research run. Returns the Query ID.
    Clients can then subscribe to /research/{id}/stream for progress events.
    """
    # Create query record in pending state
    query_record = QueryModel(
        query_text=payload.query,
        status="pending"
    )
    db.add(query_record)
    db.commit()
    db.refresh(query_record)
    
    # We will trigger the actual runner in a background task when the client connects to the stream,
    # or start it asynchronously now. Starting it via standard FastAPI BackgroundTasks or letting
    # the SSE stream drive it is clean. Let's let the SSE stream endpoint trigger it so it has access
    # to the active queue.
    return query_record


@router.get("/research/{query_id}/stream")
async def stream_research_progress(query_id: int, db: Session = Depends(get_db)):
    """
    Progressive Server-Sent Events (SSE) stream for a query run.
    """
    query_record = db.query(QueryModel).filter(QueryModel.id == query_id).first()
    if not query_record:
        raise HTTPException(status_code=404, detail="Query run not found")

    queue = asyncio.Queue()
    active_queues[query_id] = queue

    async def sse_event_generator():
        try:
            # Safe wrapper to catch exceptions and ensure client gets failed status
            async def run_safe():
                try:
                    await global_research_runner.run_research(query_record.query_text, db, queue, query_id=query_id)
                except Exception as e:
                    logger.exception(f"ResearchRunner: Exception in run_research for Query {query_id}")
                    try:
                        query_record.status = "failed"
                        db.commit()
                    except Exception:
                        db.rollback()
                    await queue.put({
                        "status": "failed",
                        "message": f"Search execution failed: {str(e)}",
                        "query_id": query_id,
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "data": None
                    })

            # Start runner task in background
            runner_task = asyncio.create_task(run_safe())
            
            while True:
                # Read status updates from queue
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    
                    if event["status"] in ["completed", "failed"]:
                        break
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield ": ping\n\n"
                    
            await runner_task
        except asyncio.CancelledError:
            logger.warning(f"SSE stream cancelled by client for Query {query_id}")
        finally:
            active_queues.pop(query_id, None)

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@router.get("/research/{query_id}", response_model=QueryResponse)
def get_query_run(query_id: int, db: Session = Depends(get_db)):
    query = db.query(QueryModel).filter(QueryModel.id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query run not found")
    return query


@router.get("/businesses", response_model=List[BusinessResponse])
def list_businesses(
    query_id: Optional[int] = None,
    min_rating: Optional[float] = None,
    min_verification_score: Optional[float] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    q = db.query(Business)
    
    if query_id:
        q = q.filter(Business.query_id == query_id)
    if min_rating:
        q = q.filter(Business.rating >= min_rating)
    if min_verification_score:
        q = q.filter(Business.verification_score >= min_verification_score)
    if search:
        q = q.filter(
            (Business.business_name.ilike(f"%{search}%")) |
            (Business.address.ilike(f"%{search}%")) |
            (Business.services.cast(func.text).ilike(f"%{search}%"))
        )
        
    return q.order_by(desc(Business.verification_score)).offset(skip).limit(limit).all()


@router.get("/businesses/{biz_id}", response_model=BusinessResponse)
def get_business(biz_id: int, db: Session = Depends(get_db)):
    biz = db.query(Business).filter(Business.id == biz_id).first()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    return biz


@router.get("/reports/{query_id}", response_model=ResearchReportResponse)
def get_report_by_query(query_id: int, db: Session = Depends(get_db)):
    report = db.query(ResearchReport).filter(ResearchReport.query_id == query_id).order_by(desc(ResearchReport.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/conflicts", response_model=List[ConflictResponse])
def list_conflicts(resolved: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(Conflict)
    if resolved is not None:
        q = q.filter(Conflict.resolved == resolved)
    return q.all()


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictResponse)
def resolve_conflict(conflict_id: int, payload: ConflictResolveRequest, db: Session = Depends(get_db)):
    conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
        
    # Update business model field value
    biz = db.query(Business).filter(Business.id == conflict.business_id).first()
    if biz:
        # Set field value on business record
        setattr(biz, conflict.field_name, payload.resolved_value)
        # Update source URL list
        source_urls = dict(biz.source_urls or {})
        source_urls[conflict.field_name] = ["manual_resolution"]
        biz.source_urls = source_urls
        # Recalculate verification score due to update
        biz.verification_score = min(biz.verification_score + 10.0, 100.0) # Bonus for manual verification

    conflict.resolved = True
    conflict.resolved_value = payload.resolved_value
    conflict.resolved_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(conflict)
    return conflict


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total_queries = db.query(func.count(QueryModel.id)).scalar() or 0
    total_businesses = db.query(func.count(Business.id)).scalar() or 0
    total_reports = db.query(func.count(ResearchReport.id)).scalar() or 0
    
    # Calculate sum of duplicates removed
    duplicates_removed_total = db.query(func.sum(ResearchReport.duplicates_removed)).scalar() or 0
    # Average duration
    avg_duration = db.query(func.avg(ResearchReport.duration)).scalar() or 0.0
    
    # Recent activity
    recent_queries = db.query(QueryModel).order_by(desc(QueryModel.created_at)).limit(5).all()
    recent_activity = [
        {
            "query_id": q.id,
            "query_text": q.query_text,
            "status": q.status,
            "created_at": q.created_at.isoformat()
        }
        for q in recent_queries
    ]
    
    return {
        "total_queries": total_queries,
        "total_businesses": total_businesses,
        "total_reports": total_reports,
        "duplicates_removed_total": int(duplicates_removed_total),
        "avg_duration": round(float(avg_duration), 1),
        "recent_activity": recent_activity
    }


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(db: Session = Depends(get_db)):
    businesses = db.query(Business).all()
    business_dicts = []
    for b in businesses:
        business_dicts.append({
            "phone": b.phone,
            "website": b.website,
            "working_hours": b.working_hours,
            "license_information": b.license_information
        })
    return global_report_generator.generate_analytics(business_dicts)


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    redis_conn = global_cache_service.is_redis_active()
    db_conn = False
    try:
        db.execute(text("SELECT 1"))
        db_conn = True
    except Exception:
        pass
        
    return {
        "status": "healthy" if db_conn else "unhealthy",
        "redis_connected": redis_conn,
        "db_connected": db_conn,
        "timestamp": datetime.datetime.utcnow()
    }


# CSV & JSON exports
@router.get("/businesses/export/csv")
def export_csv(query_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Business)
    if query_id:
        q = q.filter(Business.query_id == query_id)
        
    businesses = q.all()
    data = []
    for b in businesses:
        data.append({
            "Name": b.business_name,
            "Phone": b.phone,
            "Email": b.email,
            "Website": b.website,
            "Address": b.address,
            "Rating": b.rating,
            "Review Count": b.review_count,
            "Verification Score": b.verification_score,
            "Services": ", ".join(b.services) if b.services else "",
            "Certifications": ", ".join(b.certifications) if b.certifications else ""
        })
        
    df = pd.DataFrame(data)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=businesses_export.csv"
    return response


@router.get("/businesses/export/json")
def export_json(query_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Business)
    if query_id:
        q = q.filter(Business.query_id == query_id)
        
    businesses = q.all()
    data = []
    for b in businesses:
        data.append({
            "business_name": b.business_name,
            "phone": b.phone,
            "email": b.email,
            "website": b.website,
            "address": b.address,
            "rating": b.rating,
            "review_count": b.review_count,
            "working_hours": b.working_hours,
            "verification_score": b.verification_score,
            "services": b.services,
            "specialties": b.specialties,
            "certifications": b.certifications,
            "awards": b.awards,
            "social_profiles": b.social_profiles
        })
        
    stream = io.StringIO()
    json.dump(data, stream, indent=2)
    
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="application/json"
    )
    response.headers["Content-Disposition"] = "attachment; filename=businesses_export.json"
    return response


# Bulk Import CSV
@router.post("/businesses/import/csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))
    
    # Required columns mapping
    required_cols = ["Name"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded CSV is missing required columns: {missing}. Ensure the CSV has at least a 'Name' column."
        )

    imported_count = 0
    for _, row in df.iterrows():
        # Extracted values from row, handling NaN values
        name = str(row["Name"]) if not pd.isna(row.get("Name")) else None
        if not name or not name.strip():
            continue
            
        phone = str(row["Phone"]) if "Phone" in df.columns and not pd.isna(row.get("Phone")) else None
        email = str(row["Email"]) if "Email" in df.columns and not pd.isna(row.get("Email")) else None
        website = str(row["Website"]) if "Website" in df.columns and not pd.isna(row.get("Website")) else None
        address = str(row["Address"]) if "Address" in df.columns and not pd.isna(row.get("Address")) else None
        
        rating = float(row["Rating"]) if "Rating" in df.columns and not pd.isna(row.get("Rating")) else None
        review_count = int(row["Review Count"]) if "Review Count" in df.columns and not pd.isna(row.get("Review Count")) else None
        verification_score = float(row["Verification Score"]) if "Verification Score" in df.columns and not pd.isna(row.get("Verification Score")) else 70.0
        
        services_raw = str(row["Services"]) if "Services" in df.columns and not pd.isna(row.get("Services")) else ""
        services = [s.strip() for s in services_raw.split(",") if s.strip()] if services_raw else []
        
        cert_raw = str(row["Certifications"]) if "Certifications" in df.columns and not pd.isna(row.get("Certifications")) else ""
        certs = [c.strip() for c in cert_raw.split(",") if c.strip()] if cert_raw else []

        biz = Business(
            business_name=name,
            phone=phone,
            email=email,
            website=website,
            address=address,
            rating=rating,
            review_count=review_count,
            verification_score=verification_score,
            services=services,
            certifications=certs,
            source_urls={"manual_import": ["csv"]}
        )
        db.add(biz)
        imported_count += 1
        
    db.commit()
    return {"message": f"Successfully imported {imported_count} business records."}


@router.get("/debug/test-search")
def test_search_endpoint():
    import urllib.request
    import urllib.parse
    
    results = {}
    
    # Test 1: Google
    try:
        req = urllib.request.Request("https://www.google.com", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5.0) as response:
            results["google"] = {"status": "success", "code": response.status}
    except Exception as e:
        results["google"] = {"status": "error", "message": str(e)}

    # Test 2: Httpbin
    try:
        req = urllib.request.Request("https://httpbin.org/get", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5.0) as response:
            results["httpbin"] = {"status": "success", "code": response.status}
    except Exception as e:
        results["httpbin"] = {"status": "error", "message": str(e)}

    # Test 3: DuckDuckGo HTML
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://html.duckduckgo.com",
            "Referer": "https://html.duckduckgo.com/"
        }
        url = "https://html.duckduckgo.com/html/?q=dentists+in+austin"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5.0) as response:
            results["duckduckgo_html"] = {"status": "success", "code": response.status}
    except Exception as e:
        results["duckduckgo_html"] = {"status": "error", "message": str(e)}

    # Test 4: DuckDuckGo Lite
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = "https://lite.duckduckgo.com/lite/"
        # Lite version needs post data: q=dentists+in+austin
        data = urllib.parse.urlencode({"q": "dentists in austin"}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=5.0) as response:
            results["duckduckgo_lite"] = {"status": "success", "code": response.status}
    except Exception as e:
        results["duckduckgo_lite"] = {"status": "error", "message": str(e)}

    # Test 5: Bing
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = "https://www.bing.com/search?q=dentists+in+austin"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5.0) as response:
            results["bing"] = {"status": "success", "code": response.status}
    except Exception as e:
        results["bing"] = {"status": "error", "message": str(e)}

    # Test 6: Yahoo
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = "https://search.yahoo.com/search?p=dentists+in+austin"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5.0) as response:
            results["yahoo"] = {"status": "success", "code": response.status}
    except Exception as e:
        results["yahoo"] = {"status": "error", "message": str(e)}

    return results




