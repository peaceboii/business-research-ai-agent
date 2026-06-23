from app.services.deduplication.dedup import global_deduplicator, normalize_phone, extract_domain
from app.services.search.adapters.base import RawBusinessCandidate

def test_normalize_phone():
    assert normalize_phone("(205) 555-1234") == "2055551234"
    assert normalize_phone("+1 205-555-1234") == "2055551234"
    assert normalize_phone("12055551234") == "2055551234"
    assert normalize_phone(None) == ""

def test_extract_domain():
    assert extract_domain("https://www.google.com/search") == "google.com"
    assert extract_domain("http://yahoo.com") == "yahoo.com"
    assert extract_domain(None) == ""

def test_dedup_exact_phone():
    cand1 = RawBusinessCandidate(name="ABC Cardiology", phone="(205) 555-1111", source_name="yelp")
    cand2 = RawBusinessCandidate(name="ABC Heart Specialists", phone="12055551111", source_name="ddg")
    
    groups = global_deduplicator.group_candidates([cand1, cand2])
    assert len(groups) == 1
    assert len(groups[0]) == 2

def test_dedup_name_and_domain():
    cand1 = RawBusinessCandidate(name="ABC Cardiology", website="http://abc-cardio.com", source_name="yelp")
    cand2 = RawBusinessCandidate(name="ABC Cardiology Center", website="https://www.abc-cardio.com/contact", source_name="ddg")
    
    groups = global_deduplicator.group_candidates([cand1, cand2])
    assert len(groups) == 1

def test_dedup_no_match():
    cand1 = RawBusinessCandidate(name="ABC Cardiology", phone="2055551111", source_name="yelp")
    cand2 = RawBusinessCandidate(name="XYZ Cardiology", phone="2055552222", source_name="ddg")
    
    groups = global_deduplicator.group_candidates([cand1, cand2])
    assert len(groups) == 2
