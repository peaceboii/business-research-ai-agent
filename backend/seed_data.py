import os
import random
import datetime
import sys

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from faker import Faker
from loguru import logger

from app.database.connection import SessionLocal, Base, engine
from app.models.models import Query, Business, BusinessSource, VerificationLog, Conflict, ResearchReport

# Initialize database schema
Base.metadata.create_all(bind=engine)

def seed_db():
    db = SessionLocal()
    fake = Faker()
    
    # 1. Clean existing records to avoid cluttering dev
    logger.info("Cleaning existing database records...")
    db.query(Conflict).delete()
    db.query(VerificationLog).delete()
    db.query(BusinessSource).delete()
    db.query(Business).delete()
    db.query(ResearchReport).delete()
    db.query(Query).delete()
    db.commit()

    logger.info("Seeding database...")

    # Sample queries
    queries = [
        {"text": "Cardiologists in Birmingham", "cat": "cardiologists", "loc": "Birmingham"},
        {"text": "Dentists in Austin", "cat": "dentists", "loc": "Austin"},
        {"text": "Roofing contractors in Dallas", "cat": "roofing contractors", "loc": "Dallas"},
        {"text": "Family lawyers in Chicago", "cat": "family lawyers", "loc": "Chicago"},
        {"text": "Plumbers in Houston", "cat": "plumbers", "loc": "Houston"}
    ]

    query_orm_objects = []
    for q in queries:
        q_obj = Query(
            query_text=q["text"],
            category=q["cat"],
            location=q["loc"],
            status="completed",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(1, 10))
        )
        db.add(q_obj)
        query_orm_objects.append(q_obj)
        
    db.commit()
    for q in query_orm_objects:
        db.refresh(q)

    # Weights configuration
    sources_pool = ["website", "linkedin", "yelp", "facebook", "yellowpages", "healthgrades", "avvo", "angi"]
    
    business_prefixes = ["Apex", "First Class", "Summit", "Lakeside", "Metro", "Choice", "Valley", "Elite", "Pro", "Direct"]
    business_suffixes = ["Group", "Center", "Partners", "Clinic", "Associates", "Experts", "Solutions", "Professionals"]

    total_records = 500
    records_per_query = total_records // len(query_orm_objects)
    
    logger.info(f"Generating {total_records} business records ({records_per_query} per category)...")

    for q_idx, q_obj in enumerate(query_orm_objects):
        cat = q_obj.category
        loc = q_obj.location
        cat_title = cat.title()
        loc_title = loc.title()
        
        businesses_to_add = []
        
        for i in range(records_per_query):
            # Generate Business Name
            if "cardiologist" in cat:
                name = f"Dr. {fake.first_name()} {fake.last_name()}, MD"
            elif "dentist" in cat:
                name = f"Dr. {fake.first_name()} {fake.last_name()}, DDS"
            elif "lawyer" in cat or "attorney" in cat:
                name = f"{fake.last_name()} & {fake.last_name()} Legal Group"
                if i % 3 == 0:
                    name = f"{fake.first_name()} {fake.last_name()}, Esq."
            elif "plumber" in cat:
                name = f"{fake.last_name()} Plumbers & Gasfitters"
                if i % 2 == 0:
                    name = f"All-Clear Plumbing {loc_title}"
            else:
                name = f"{random.choice(business_prefixes)} {cat_title} {random.choice(business_suffixes)}"

            # Phone
            area_code = random.randint(200, 999)
            phone = f"({area_code}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
            
            # Domain and Website
            domain = name.lower().replace(" ", "").replace(",", "").replace(".", "").replace("&", "and")
            website = f"https://www.{domain}.com"
            
            # Email
            email = f"info@{domain}.com"
            
            # Address
            address = f"{random.randint(100, 9999)} {fake.street_name()}, {loc_title}, {fake.state_abbr()} {random.randint(10000, 99999)}"
            
            # Services
            services = [f"{cat_title} Consultation", f"Emergency {cat_title} Services"]
            if "plumber" in cat:
                services.extend(["Leak Detection", "Pipe Installation", "Water Heater Repair"])
            elif "lawyer" in cat:
                services.extend(["Contract Review", "Litigation Support", "Client Representation"])
            elif "cardiologist" in cat:
                services.extend(["Echocardiogram", "Heart Rate Monitor", "Cardiovascular Checkup"])
            elif "dentist" in cat:
                services.extend(["Teeth Cleaning", "Root Canal", "Dental Crown"])
            elif "roofing" in cat:
                services.extend(["Roof Replacement", "Leak Patching", "Gutter Maintenance"])

            # Social Profiles
            socials = []
            if random.choice([True, False]):
                socials.append(f"https://facebook.com/{domain}")
            if random.choice([True, False]):
                socials.append(f"https://linkedin.com/company/{domain}")

            # Rating / Review count
            rating = round(random.uniform(3.5, 5.0), 1)
            review_count = random.randint(5, 450)

            # Verification score
            v_score = round(random.uniform(50.0, 100.0), 1)

            # Working Hours
            working_hours = {
                "Monday": "8:00 AM - 5:00 PM",
                "Tuesday": "8:00 AM - 5:00 PM",
                "Wednesday": "8:00 AM - 5:00 PM",
                "Thursday": "8:00 AM - 5:00 PM",
                "Friday": "8:00 AM - 5:00 PM"
            }
            if random.choice([True, False]):
                working_hours["Saturday"] = "9:00 AM - 1:00 PM"

            # Create source links structure
            source_urls_mapping = {
                "phone": [website, f"https://yelp.com/biz/{domain}"],
                "website": [website],
                "address": [f"https://yellowpages.com/biz/{domain}", website]
            }

            biz = Business(
                query_id=q_obj.id,
                business_name=name,
                address=address,
                phone=phone,
                email=email,
                website=website,
                working_hours=working_hours,
                rating=rating,
                review_count=review_count,
                services=services,
                specialties=[cat_title],
                license_information=f"LIC-{random.randint(100000, 999999)}" if random.random() > 0.3 else None,
                certifications=[f"Board Certified {cat_title}"] if "cardiologist" in cat or "dentist" in cat else ["Licensed & Insured"],
                awards=[f"Top Rated {cat_title} {loc_title}"] if random.random() > 0.7 else [],
                social_profiles=socials,
                image_urls=[f"https://picsum.photos/seed/{domain}/300/200"],
                source_urls=source_urls_mapping,
                verification_score=v_score,
                created_at=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 5))
            )
            
            db.add(biz)
            businesses_to_add.append(biz)
            
        db.commit()
        
        # Seed related sources, verifications, and conflicts
        for biz in businesses_to_add:
            # 2. Add Sources
            num_sources = random.randint(2, 4)
            chosen_sources = random.sample(sources_pool, num_sources)
            
            for sname in chosen_sources:
                src = BusinessSource(
                    business_id=biz.id,
                    source_name=sname,
                    url=f"https://www.{sname}.com/biz/{domain}",
                    rating=round(biz.rating + random.uniform(-0.5, 0.5), 1),
                    review_count=max(1, int(biz.review_count * random.uniform(0.5, 1.5))),
                    address=biz.address if random.random() > 0.2 else None,
                    phone=biz.phone if random.random() > 0.1 else None,
                    email=biz.email if random.random() > 0.5 else None,
                    working_hours=biz.working_hours if random.random() > 0.4 else None,
                    services=biz.services,
                    specialties=biz.specialties
                )
                db.add(src)

            # 3. Add verification logs
            for field in ["phone", "address", "website"]:
                for sname in chosen_sources:
                    vlog = VerificationLog(
                        business_id=biz.id,
                        field_name=field,
                        source=sname,
                        value=getattr(biz, field),
                        is_valid=True
                    )
                    db.add(vlog)

            # 4. Generate some mock conflicts for 5% of records
            if random.random() < 0.05:
                conflicting_phone = f"({area_code}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
                conflict = Conflict(
                    business_id=biz.id,
                    field_name="phone",
                    conflicting_values=[biz.phone, conflicting_phone],
                    resolved=False
                )
                db.add(conflict)

        # 5. Generate query research report
        duration = random.uniform(8.5, 22.0)
        duplicates_removed = random.randint(5, 30)
        sources_used = random.randint(4, 8)
        
        analytics = {
            "records_with_phone": sum(1 for b in businesses_to_add if b.phone),
            "records_with_website": sum(1 for b in businesses_to_add if b.website),
            "records_with_hours": sum(1 for b in businesses_to_add if b.working_hours),
            "records_with_license": sum(1 for b in businesses_to_add if b.license_information),
        }
        total = len(businesses_to_add)
        
        md_report = f"""# Research Report: {q_obj.query_text}
## Executive Summary
This report summarizes the discoveries and field-level verification for the query **"{q_obj.query_text}"**.
An autonomous crawling agent extracted business profiles, cross-checked contact numbers against local and global directory profiles, and performed fuzzy deduplication.

---

## Research Statistics
* **Query:** {q_obj.query_text}
* **Businesses Discovered:** {total + duplicates_removed}
* **Unique Verified Entities:** {total}
* **Duplicates Removed:** {duplicates_removed}
* **Sources Utilized:** {sources_used}
* **Duration:** {duration:.2f} seconds

---

## Data Quality Summary
* **Website coverage:** {analytics["records_with_website"] / total * 100.0:.1f}%
* **Phone coverage:** {analytics["records_with_phone"] / total * 100.0:.1f}%
* **Hours coverage:** {analytics["records_with_hours"] / total * 100.0:.1f}%
"""
        report = ResearchReport(
            query_id=q_obj.id,
            duration=duration,
            total_discovered=total + duplicates_removed,
            total_verified=total,
            duplicates_removed=duplicates_removed,
            sources_used=sources_used,
            website_coverage=round(analytics["records_with_website"] / total * 100.0, 1),
            phone_coverage=round(analytics["records_with_phone"] / total * 100.0, 1),
            hours_coverage=round(analytics["records_with_hours"] / total * 100.0, 1),
            report_markdown=md_report
        )
        db.add(report)
        db.commit()

    logger.info("Database seeding completed successfully!")
    db.close()

if __name__ == "__main__":
    seed_db()
